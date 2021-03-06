
/* String object interface */

#ifndef Py_STRINGOBJECT_H
#define Py_STRINGOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyString_GET_SIZE(op) PyString_Size((PyObject*)(op))
#define PyString_AS_STRING(op) PyString_AsString((PyObject*)(op))

typedef struct {
    PyObject_HEAD
    char* buffer;
    Py_ssize_t size;
} PyStringObject;

PyAPI_FUNC(PyObject *) PyString_FromFormatV(const char *format, va_list vargs);
PyAPI_FUNC(PyObject *) PyString_FromFormat(const char *format, ...);

#ifdef __cplusplus
}
#endif
#endif
