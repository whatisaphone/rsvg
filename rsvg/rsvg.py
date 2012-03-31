import ctypes
from . import lib


class RSVG:
    def __init__(self, data=None):
        self.handle = lib.rsvg.rsvg_handle_new()
        if data:
            self.write(data)
            self.close()

    def __del__(self):
        self.free()

    def free(self):
        if self.handle:
            lib.gobject.g_object_unref(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.free()

    def write(self, data):
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        if not lib.rsvg.rsvg_handle_write(self.handle, data, len(data), None):
            raise ValueError

    def close(self):
        if not lib.rsvg.rsvg_handle_close(self.handle, None):
            raise ValueError


    @property
    def size(self):
        dimensions = lib.RsvgDimensionData()
        lib.rsvg.rsvg_handle_get_dimensions(self.handle, dimensions)
        return dimensions.width, dimensions.height


    def render_pixbuf(self, *, size=None):
        if size:
            raise ValueError("can't set size when rendering using pixbuf")

        pixbuf = lib.rsvg.rsvg_handle_get_pixbuf(self.handle)
        try:
            self.buffer = []
            callback = lib.GdkPixbufSaveFunc(self.render_pixbuf_callback)
            if not lib.gdk_pixbuf.gdk_pixbuf_save_to_callbackv(pixbuf,
                    callback, None, b'png', None, None, None):
                raise ValueError
            return b''.join(self.buffer)
        finally:
            lib.gobject.g_object_unref(pixbuf)

    def render_pixbuf_callback(self, buf, count, error, data):
        self.buffer.append(ctypes.string_at(buf, count))
        return True


    def render_cairo(self, *, size=None):
        w, h = self.size
        surface = lib.cairo.cairo_image_surface_create(lib.CAIRO_FORMAT_ARGB32,
                                                       size or w, size or h)
        try:
            if lib.cairo.cairo_surface_status(surface) != lib.CAIRO_STATUS_SUCCESS:
                raise ValueError

            cairo = lib.cairo.cairo_create(surface)
            try:
                if lib.cairo.cairo_status(cairo) != lib.CAIRO_STATUS_SUCCESS:
                    raise ValueError

                if size:
                    lib.cairo.cairo_scale(cairo, size / w, size / h)
                if not lib.rsvg.rsvg_handle_render_cairo(self.handle, cairo):
                    raise ValueError

                self.buffer = []
                callback = lib.cairo_write_func_t(self.render_cairo_callback)
                if lib.cairo.cairo_surface_write_to_png_stream(
                        surface, callback, None):
                    raise ValueError
                return b''.join(self.buffer)
            finally:
                lib.cairo.cairo_destroy(cairo)
        finally:
            lib.cairo.cairo_surface_destroy(surface)

    def render_cairo_callback(self, closure, data, length):
        self.buffer.append(ctypes.string_at(data, length))
        return lib.CAIRO_STATUS_SUCCESS


    to_png = render_cairo
