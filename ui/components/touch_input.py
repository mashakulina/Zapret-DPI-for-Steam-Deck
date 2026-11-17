"""Application-local XI2 touch delivery for Tk running through XWayland.

XI2 TouchEnd represents both physical release and some logical cancellations;
the protocol does not expose Wayland's separate touch-cancel reason. Pending
ownership, hidden/destroyed targets, focus loss and modal changes are cancelled
without activating buttons. No raw events or X root windows are subscribed.
"""
from collections import deque
import ctypes as C
import ctypes.util
import os
import sys
import time
import tkinter as tk

from core.app_logging import get_error_logger


class TouchInputUnavailable(RuntimeError):
    """The current display cannot provide application-local native touch."""


class _XIEventMask(C.Structure):
    _fields_ = [('deviceid', C.c_int), ('mask_len', C.c_int),
                ('mask', C.POINTER(C.c_ubyte))]


class _XCookie(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', C.c_ulong),
                ('send_event', C.c_int), ('display', C.c_void_p),
                ('extension', C.c_int), ('evtype', C.c_int),
                ('cookie', C.c_uint), ('data', C.c_void_p)]


class _XEvent(C.Union):
    _fields_ = [('type', C.c_int), ('cookie', _XCookie), ('pad', C.c_long * 24)]


class _XITouchPrefix(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', C.c_ulong),
                ('send_event', C.c_int), ('display', C.c_void_p),
                ('extension', C.c_int), ('evtype', C.c_int),
                ('time', C.c_ulong), ('deviceid', C.c_int),
                ('sourceid', C.c_int), ('detail', C.c_int),
                ('root', C.c_ulong), ('event', C.c_ulong),
                ('child', C.c_ulong), ('root_x', C.c_double),
                ('root_y', C.c_double), ('event_x', C.c_double),
                ('event_y', C.c_double), ('flags', C.c_int)]


class _XError(C.Structure):
    _fields_ = [('type', C.c_int), ('display', C.c_void_p),
                ('resourceid', C.c_ulong), ('serial', C.c_ulong),
                ('error_code', C.c_ubyte), ('request_code', C.c_ubyte),
                ('minor_code', C.c_ubyte)]


class _Xi2Connection:
    """Private X connection selecting native touch on explicitly owned XIDs."""
    _ERROR_CALLBACK = C.CFUNCTYPE(C.c_int, C.c_void_p, C.POINTER(_XError))

    def __init__(self):
        self.display = None
        self.windows = set()
        self.xlib = C.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
        self.xi = C.CDLL(ctypes.util.find_library('Xi') or 'libXi.so.6')
        declarations = {
            'XOpenDisplay': ([C.c_char_p], C.c_void_p),
            'XCloseDisplay': ([C.c_void_p], C.c_int),
            'XConnectionNumber': ([C.c_void_p], C.c_int),
            'XQueryExtension': ([C.c_void_p, C.c_char_p, C.POINTER(C.c_int),
                                C.POINTER(C.c_int), C.POINTER(C.c_int)], C.c_int),
            'XPending': ([C.c_void_p], C.c_int),
            'XNextEvent': ([C.c_void_p, C.POINTER(_XEvent)], C.c_int),
            'XGetEventData': ([C.c_void_p, C.POINTER(_XCookie)], C.c_int),
            'XFreeEventData': ([C.c_void_p, C.POINTER(_XCookie)], None),
            'XSync': ([C.c_void_p, C.c_int], C.c_int),
            'XSetErrorHandler': ([C.c_void_p], C.c_void_p),
        }
        for name, (arguments, result) in declarations.items():
            function = getattr(self.xlib, name)
            function.argtypes, function.restype = arguments, result
        self.xi.XIQueryVersion.argtypes = [C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_int)]
        self.xi.XIQueryVersion.restype = C.c_int
        self.xi.XISelectEvents.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(_XIEventMask), C.c_int]
        self.xi.XISelectEvents.restype = C.c_int
        try:
            self.display = self.xlib.XOpenDisplay(None)
            if not self.display:
                raise TouchInputUnavailable('Cannot open the current X display')
            opcode, first_event, first_error = C.c_int(), C.c_int(), C.c_int()
            if not self.xlib.XQueryExtension(self.display, b'XInputExtension',
                                            C.byref(opcode), C.byref(first_event), C.byref(first_error)):
                raise TouchInputUnavailable('XInput extension unavailable')
            self.opcode = opcode.value
            major, minor = C.c_int(2), C.c_int(2)
            status = self._checked(lambda: self.xi.XIQueryVersion(
                self.display, C.byref(major), C.byref(minor)))
            if status or (major.value, minor.value) < (2, 2):
                raise TouchInputUnavailable('XI2 version 2.2 is required')
        except Exception:
            self.close()
            raise

    def _checked(self, request):
        errors = []
        previous = None

        def on_error(display, pointer):
            if display == self.display:
                error = pointer.contents
                errors.append((error.error_code, error.request_code, error.minor_code))
                return 0
            return self._ERROR_CALLBACK(previous)(display, pointer) if previous else 0

        callback = self._ERROR_CALLBACK(on_error)
        # Xlib error handlers are process-wide. Keep this replacement scoped
        # to one synchronous own-display request; preserve Tk's handler.
        previous = self.xlib.XSetErrorHandler(C.cast(callback, C.c_void_p))
        try:
            result = request()
            self.xlib.XSync(self.display, False)
        finally:
            self.xlib.XSetErrorHandler(previous)
        if errors:
            raise TouchInputUnavailable(f'XInput request failed: {errors}')
        return result

    def fileno(self):
        return self.xlib.XConnectionNumber(self.display)

    def has_pending(self):
        return bool(self.display and self.xlib.XPending(self.display))

    def select_windows(self, windows):
        bits = (C.c_ubyte * 3)()
        for event_type in (18, 19, 20):
            bits[event_type >> 3] |= 1 << (event_type & 7)
        mask = _XIEventMask(1, 3, bits)  # XIAllMasterDevices: avoid slave/master duplicates.
        for window in set(windows) - self.windows:
            self._checked(lambda window=window: self.xi.XISelectEvents(
                self.display, window, C.byref(mask), 1))
        # Removed XIDs belong to destroyed Tk windows; X automatically drops
        # their selections. Closing this connection releases all remaining ones.
        self.windows = set(windows)

    def read_events(self, limit=256):
        events = []
        for _ in range(limit):
            if not self.display or not self.xlib.XPending(self.display):
                break
            event = _XEvent()
            self.xlib.XNextEvent(self.display, C.byref(event))
            if event.type != 35:
                continue
            cookie = event.cookie
            if not self.xlib.XGetEventData(self.display, C.byref(cookie)):
                continue
            try:
                if cookie.extension == self.opcode and cookie.evtype in (18, 19, 20):
                    native = C.cast(cookie.data, C.POINTER(_XITouchPrefix)).contents
                    # Do not discard End for a destroyed target: it still
                    # releases first-contact bookkeeping after a press callback.
                    events.append({name: getattr(native, name) for name in (
                        'evtype', 'time', 'deviceid', 'sourceid', 'detail',
                        'event', 'root_x', 'root_y', 'flags')})
            finally:
                self.xlib.XFreeEventData(self.display, C.byref(cookie))
        return events

    def close(self):
        if self.display:
            self.xlib.XCloseDisplay(self.display)
            self.display = None
        self.windows.clear()


class TouchInputController:
    """Translate one primary native touch into the existing Tk class bindings.

    ``transport`` is injectable for tests; it supplies fileno/select_windows/
    read_events/close. ``handle_touch`` accepts normalized XI2 event dictionaries.
    All methods and the private X connection run on Tk's main thread.
    """
    BUTTON1 = 1 << 8
    PENDING_END = 1 << 16

    def __init__(self, root, transport=None):
        self.root, self.tk = root, root.tk
        self.root_path = root._w
        self.closed = False
        self.transport = None
        self.windows = {}
        self.contacts = set()
        self.active = None
        self.pending = deque()
        self._jobs = {}
        self._bindings = []
        self._filehandler = False
        self._fd = None
        self._failed = False
        self._refreshing = False
        self._refresh_requested = False
        try:
            self.transport = transport if transport is not None else _Xi2Connection()
            self._refresh_windows()
            self._fd = self.transport.fileno()
            if self._fd is not None and hasattr(self.tk, 'createfilehandler'):
                self.tk.createfilehandler(self._fd, tk.READABLE, self._readable)
                self._filehandler = True
            else:
                self._schedule('poll', 8, self._poll)
            for sequence, callback in (('<Map>', self._mapped),
                                       ('<Unmap>', self._validate_later),
                                       ('<Destroy>', self._destroyed),
                                       ('<FocusOut>', self._validate_later)):
                self._bindings.append((sequence, root.bind_all(sequence, callback, add='+')))
            self._schedule('read', 0, self._readable)
        except Exception:
            self.close()
            raise

    def _schedule(self, name, delay, callback):
        if self.closed or name in self._jobs:
            return

        def run():
            self._jobs.pop(name, None)
            if not self.closed:
                callback()

        self._jobs[name] = (self.root.after_idle(run) if delay == 'idle'
                            else self.root.after(delay, run))

    def _discover_windows(self):
        result, remaining = {}, [self.root_path]
        while remaining:
            path = remaining.pop()
            if self._exists(path):
                result[int(str(self.tk.call('winfo', 'id', path)), 0)] = path
                remaining.extend(self.tk.splitlist(self.tk.call('winfo', 'children', path)))
        return result

    def _refresh_windows(self):
        if self._refreshing:
            self._refresh_requested = True
            return
        self._refreshing = True
        try:
            windows = self._discover_windows()
            # winfo id lazily creates windows. Synchronize the owner connection
            # before subscribing to their XIDs from the private connection.
            self.root.update_idletasks()
            if self.closed:
                return
            windows = {xid: path for xid, path in windows.items()
                       if self._exists(path) and self._xid(path) == xid}
            self.transport.select_windows(set(windows))
            self.windows = windows
        finally:
            self._refreshing = False
        if self._refresh_requested:
            self._refresh_requested = False
            self._schedule('refresh', 'idle', self._refresh_safely)

    def _mapped(self, event):
        if self._refreshing:
            self._refresh_requested = True
        else:
            self._schedule('refresh', 'idle', self._refresh_safely)

    def _refresh_safely(self):
        try:
            self._refresh_windows()
            self._readable()
        except Exception as exc:
            self._fail(exc)

    def _destroyed(self, event):
        if str(event.widget) == self.root_path:
            self.close()
        else:
            self._validate_later(event)

    def _validate_later(self, event):
        self._schedule('validate', 'idle', self._validate_active)

    def _validate_active(self):
        if self.active and not self._allowed(self.active['pressed']):
            self._cancel(clear_contacts=True)
        elif self.active and not self.tk.call('focus', '-displayof', self.root_path):
            self._cancel(clear_contacts=True)

    def _readable(self, *args):
        if self.closed:
            return
        try:
            events = self.transport.read_events(limit=256)
            for event in events:
                if (event['evtype'] == 19 and not event.get('flags', 0) & self.PENDING_END
                        and self.pending and self.pending[-1]['evtype'] == 19
                        and not self.pending[-1].get('flags', 0) & self.PENDING_END
                        and (event['deviceid'], event['detail'])
                        == (self.pending[-1]['deviceid'], self.pending[-1]['detail'])):
                    self.pending[-1] = event
                else:
                    self.pending.append(event)
            if len(self.pending) > 1024:
                raise TouchInputUnavailable('Native touch queue overflow')
            if self.pending:
                self._schedule('dispatch', 0, self._dispatch_one)
            has_pending = getattr(self.transport, 'has_pending', None)
            if len(events) == 256 or (has_pending is not None and has_pending()):
                self._schedule('read', 0, self._readable)
        except Exception as exc:
            self._fail(exc)

    def _poll(self):
        self._readable()
        self._schedule('poll', 8, self._poll)

    def _dispatch_one(self):
        if not self.pending:
            return
        event = self.pending.popleft()
        if self.pending:
            # Queue before invoking bindings: callbacks may call wait_window.
            self._schedule('dispatch', 0, self._dispatch_one)
        try:
            self.handle_touch(event)
        except tk.TclError as exc:
            if self._exists(self.root_path):
                self._fail(exc)
            else:
                self.close()

    def _exists(self, path):
        try:
            return bool(int(self.tk.call('winfo', 'exists', path)))
        except tk.TclError:
            return False

    def _xid(self, path):
        return int(str(self.tk.call('winfo', 'id', path)), 0)

    def _descendant(self, path, ancestor):
        while path:
            if path == ancestor:
                return True
            path = str(self.tk.call('winfo', 'parent', path))
        return False

    def _allowed(self, path):
        if not path or not self._exists(path):
            return False
        try:
            if not int(self.tk.call('winfo', 'viewable', path)):
                return False
            if not self._descendant(path, self.root_path):
                return False
            grab = str(self.tk.call('grab', 'current', self.root_path))
            if grab and not self._descendant(path, grab):
                return False
            if str(self.tk.call('winfo', 'class', path)).startswith('T'):
                try:
                    return not bool(int(self.tk.call(path, 'instate', 'disabled')))
                except tk.TclError:
                    pass
            try:
                return str(self.tk.call(path, 'cget', '-state')) != 'disabled'
            except tk.TclError:
                return True
        except tk.TclError:
            return False

    def _hit(self, x, y):
        path = str(self.tk.call('winfo', 'containing', '-displayof', self.root_path,
                                round(x), round(y)))
        return path if self._allowed(path) else None

    def _emit(self, path, sequence, x, y, state=0, timestamp=None):
        if not path or not self._exists(path):
            return
        timestamp = int(time.monotonic() * 1000) if timestamp is None else timestamp
        arguments = ['event', 'generate', path, sequence,
                     '-x', round(x - int(self.tk.call('winfo', 'rootx', path))),
                     '-y', round(y - int(self.tk.call('winfo', 'rooty', path))),
                     '-rootx', round(x), '-rooty', round(y), '-state', state,
                     '-time', int(timestamp) & 0xffffffff, '-when', 'now']
        if sequence in ('<ButtonPress-1>', '<ButtonRelease-1>', '<Motion>'):
            arguments.extend(('-warp', False))
        self.tk.call(*arguments)

    def _hover(self, active, path, x, y, timestamp):
        previous = active['hover']
        if previous == path:
            return
        self._emit(previous, '<Leave>', x, y, self.BUTTON1, timestamp)
        active['hover'] = path
        self._emit(path, '<Enter>', x, y, self.BUTTON1, timestamp)

    def handle_touch(self, event):
        """Handle an XI2 dictionary; exposed so tests exercise real Tk bindings."""
        if self.closed:
            return
        kind = event['evtype']
        key = (event['deviceid'], event['detail'])
        x, y = event['root_x'], event['root_y']
        timestamp = event.get('time', int(time.monotonic() * 1000))
        if kind == 18:
            if self.active and not self._allowed(self.active['pressed']):
                self._cancel(clear_contacts=True)
            owner = self.windows.get(event['event']) if 'event' in event else None
            if 'event' in event and (not self._allowed(owner) or self._xid(owner) != event['event']):
                return
            path = self._hit(x, y)
            if path is None:
                return
            if owner and (not self._descendant(path, owner)
                          or self.tk.call('winfo', 'toplevel', path)
                          != self.tk.call('winfo', 'toplevel', owner)):
                return
            first = not self.contacts
            self.contacts.add(key)
            if not first:
                return
            self.active = {'key': key, 'pressed': path, 'hover': path,
                           'xy': (x, y), 'time': timestamp}
            self._emit(path, '<Enter>', x, y, timestamp=timestamp)
            self._emit(path, '<ButtonPress-1>', x, y, timestamp=timestamp)
            return
        if kind == 20:
            self.contacts.discard(key)
        active = self.active
        if active is None or active['key'] != key:
            return
        active.update(xy=(x, y), time=timestamp)
        if event.get('flags', 0) & self.PENDING_END:
            self._cancel()
            return
        if not self._allowed(active['pressed']):
            self._cancel(clear_contacts=True)
            return
        target = self._hit(x, y)
        self._hover(active, target, x, y, timestamp)
        if kind == 19:
            self._emit(active['pressed'], '<Motion>', x, y, self.BUTTON1, timestamp)
        elif kind == 20:
            tags = self.tk.splitlist(self.tk.call('bindtags', active['pressed']))
            if 'ComboboxListbox' in tags and target != active['pressed']:
                self._cancel()
                return
            self.active = None
            self._emit(active['pressed'], '<ButtonRelease-1>', x, y, self.BUTTON1, timestamp)
            self._emit(active['hover'], '<Leave>', x, y, timestamp=timestamp)

    def _cancel(self, *, clear_contacts=False):
        active, self.active = self.active, None
        if clear_contacts:
            self.contacts.clear()
        if active is None:
            return
        self.contacts.discard(active['key'])
        path, (x, y), timestamp = active['pressed'], active['xy'], active['time']
        if not self._exists(path):
            # A destroyed touch owner may never get another native End.
            self.contacts.discard(active['key'])
            return
        try:
            tags = self.tk.splitlist(self.tk.call('bindtags', path))
            if active['hover'] == path:
                self._emit(path, '<Leave>', x, y, self.BUTTON1, timestamp)
            if 'ComboboxListbox' in tags:
                # Its release binding commits selection unconditionally.
                self.tk.call('tk::CancelRepeat')
                self.tk.call('ttk::combobox::LBCancel', path)
            elif str(self.tk.call('winfo', 'class', path)) != 'TCombobox':
                self._emit(path, '<ButtonRelease-1>', -100, -100, self.BUTTON1, timestamp)
            self._emit(active['hover'], '<Leave>', x, y, timestamp=timestamp)
        except tk.TclError:
            pass

    def _fail(self, error):
        if not self._failed:
            self._failed = True
            get_error_logger().error('Отключена совместимость сенсора XI2: %s', error)
        self.close()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self._cancel()
        for identifier in self._jobs.values():
            try:
                self.root.after_cancel(identifier)
            except tk.TclError:
                pass
        self._jobs.clear()
        if self._filehandler:
            self.tk.deletefilehandler(self._fd)
        for sequence, identifier in self._bindings:
            try:
                self.root._unbind(('bind', 'all', sequence), identifier)
            except tk.TclError:
                pass
        self._bindings.clear()
        if self.transport is not None:
            self.transport.close()
        self.windows.clear()
        self.pending.clear()
        self.contacts.clear()


def install_touch_support(root):
    """Install once for Wayland/X11 Tk; X11 sessions never load XInput libraries."""
    if (not sys.platform.startswith('linux')
            or os.environ.get('XDG_SESSION_TYPE', '').lower() != 'wayland'
            or os.environ.get('ZAPRET_TOUCH_INPUT', '').lower() in ('off', '0', 'false', 'no')):
        return None
    if getattr(root, '_touch_input_attempted', False):
        controller = getattr(root, '_touch_input_controller', None)
        return controller if controller is not None and not controller.closed else None
    if root.tk.call('tk', 'windowingsystem') != 'x11':
        return None
    root._touch_input_attempted = True
    try:
        controller = TouchInputController(root)
    except (OSError, AttributeError, tk.TclError, TouchInputUnavailable) as exc:
        get_error_logger().error('Не удалось включить совместимость сенсора XI2: %s', exc)
        return None
    root._touch_input_controller = controller
    return controller
