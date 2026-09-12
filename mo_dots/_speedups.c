/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
 *
 * Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
 *
 * C ACCELERATORS FOR mo_dots
 *
 * Pure-Python equivalents remain in the .py modules; this module is optional
 * and the package falls back when absent (MO_DOTS_PURE=1 forces the fallback).
 * Semantics must match the Python versions exactly - the test suite is the
 * conformance test.
 *
 * Two layers:
 *  - hot functions: is_null, is_missing, to_data, from_data, ...
 *  - hot base types: _StoreBase (single slot, shared by Data and FlatList so
 *    __class__ reassignment keeps compatible layouts), _DataBase (C getattro/
 *    setattro/subscript/bool), _NullBase (C slots for nearly every dunder).
 *    The Python classes are rebuilt as subclasses; their pure methods remain
 *    as the slow path for exotic cases (dotted paths, non-dict slots).
 *
 * Wiring: utils.py imports this and calls _sync() on every type registration;
 * nones/datas/lists call _init_null/_init_data/_init_list as their classes are
 * built; mo_dots/__init__.py calls _init() once everything exists, then
 * rebinds the module-level functions before export() distributes them.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>
#include <stddef.h> /* offsetof; NOT TRANSITIVE FROM Python.h ON gcc/3.12+ */

#if PY_VERSION_HEX >= 0x030C0000
#define MEMBER_OBJ_EX Py_T_OBJECT_EX
#else
#include <structmember.h>
#define MEMBER_OBJ_EX T_OBJECT_EX
#endif

typedef struct {
    PyObject_HEAD
    PyObject *store; /* _internal_value */
} StoreObject;

typedef struct {
    PyObject_HEAD
    PyObject *store; /* _internal_value */
    PyObject *key;   /* _key */
} NullObject;

#define STORE(op) (((StoreObject *)(op))->store)
#define NKEY(op) (((NullObject *)(op))->key)

static PyObject *DataClass = NULL;       /* final mo_dots.datas.Data     */
static PyObject *FlatListClass = NULL;   /* final mo_dots.lists.FlatList */
static PyObject *NullTypeClass = NULL;   /* final mo_dots.nones.NullType */
static PyObject *NullSingleton = NULL;   /* mo_dots.nones.Null           */
static PyObject *DataObjectClass = NULL; /* mo_dots.objects.DataObject   */
static PyObject *OrderedDictClass = NULL;
static PyObject *generator_types = NULL; /* tuple of generator classes   */
static PyObject *from_data_gen = NULL;   /* lazy generator helper        */
static PyObject *slot_str = NULL;        /* "_internal_value"            */
static PyObject *empty_tuple = NULL;
static PyObject *empty_str = NULL;
static PyObject *null_repr_str = NULL;
static Py_hash_t null_hash = 0;

static PyObject *null_types_tuple = NULL;    /* tuple of null classes    */
static PyObject *missing_types_tuple = NULL; /* (str, *null, *many)      */
static PyObject *sequence_types_tuple = NULL;
static PyObject *data_types_tuple = NULL;    /* is_data() classes        */
static PyObject *many_types_tuple = NULL;    /* is_many() classes        */

/* PURE-PYTHON SLOW PATHS (THE ORIGINAL METHODS) */
static PyObject *null_getattr_slow = NULL;
static PyObject *null_getitem_slow = NULL;
static PyObject *data_getattr_slow = NULL;
static PyObject *data_getitem_slow = NULL;
static PyObject *data_setitem_slow = NULL;
static PyObject *data_delitem_slow = NULL;
static PyObject *data_items_slow = NULL;
static PyObject *flatlist_get_slow = NULL;
static PyObject *dot_str = NULL;  /* "." */
static PyObject *json_str = NULL; /* "__json__" */
static PyObject *call_str = NULL; /* "__call__" */
static PyObject *list_contains_meth = NULL; /* list.__contains__ descriptor */

static PyTypeObject StoreBase_Type;
static PyTypeObject DataBase_Type;
static PyTypeObject NullBase_Type;


static inline int
type_in_tuple(PyTypeObject *t, PyObject *tuple)
{
    Py_ssize_t i, n;
    if (tuple == NULL)
        return 0;
    n = PyTuple_GET_SIZE(tuple);
    for (i = 0; i < n; i++) {
        if (PyTuple_GET_ITEM(tuple, i) == (PyObject *)t)
            return 1;
    }
    return 0;
}


/* LOOK name UP THE MRO'S TYPE DICTS; NEW REF, NULL ON MISS (CHECK PyErr) */
static PyObject *
mro_lookup(PyTypeObject *tp, PyObject *name)
{
    PyObject *mro = tp->tp_mro;
    Py_ssize_t i, n;
    if (mro == NULL)
        return NULL;
    n = PyTuple_GET_SIZE(mro);
    for (i = 0; i < n; i++) {
        PyTypeObject *base = (PyTypeObject *)PyTuple_GET_ITEM(mro, i);
        PyObject *res;
#if PY_VERSION_HEX >= 0x030C0000
        PyObject *dict = PyType_GetDict(base);
#else
        PyObject *dict = base->tp_dict;
        Py_XINCREF(dict);
#endif
        if (dict == NULL)
            continue;
        res = PyDict_GetItemWithError(dict, name);
        Py_XINCREF(res);
        Py_DECREF(dict);
        if (res != NULL)
            return res;
        if (PyErr_Occurred())
            return NULL;
    }
    return NULL;
}


/* type-attr access equivalent to the successful part of object.__getattribute__ */
static PyObject *
bind_type_attr(PyObject *self, PyObject *name, int *found)
{
    descrgetfunc f;
    PyObject *descr = mro_lookup(Py_TYPE(self), name);
    if (descr == NULL) {
        *found = PyErr_Occurred() ? 1 : 0; /* real error: caller returns NULL */
        return NULL;
    }
    *found = 1;
    f = Py_TYPE(descr)->tp_descr_get;
    if (f != NULL) {
        PyObject *res = f(descr, self, (PyObject *)Py_TYPE(self));
        Py_DECREF(descr);
        return res;
    }
    return descr;
}


/* ================= INSTANCE CREATION (NO __init__, NO __setattr__) ========= */

static PyObject *
new_store(PyObject *cls, PyObject *value)
{
    PyTypeObject *tp = (PyTypeObject *)cls;
    PyObject *m = tp->tp_alloc(tp, 0);
    if (m == NULL)
        return NULL;
    Py_INCREF(value);
    STORE(m) = value;
    return m;
}


static PyObject *
new_null(PyObject *obj, PyObject *key)
{
    PyTypeObject *tp = (PyTypeObject *)NullTypeClass;
    PyObject *m;
    if (tp == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "mo_dots._speedups not initialized");
        return NULL;
    }
    m = tp->tp_alloc(tp, 0);
    if (m == NULL)
        return NULL;
    Py_INCREF(obj);
    STORE(m) = obj;
    Py_INCREF(key);
    NKEY(m) = key;
    return m;
}


/* ======================= HOT FUNCTIONS ==================================== */

static PyObject *
speedups_is_null(PyObject *self, PyObject *v)
{
    if (type_in_tuple(Py_TYPE(v), null_types_tuple))
        Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}


static PyObject *
speedups_is_not_null(PyObject *self, PyObject *v)
{
    if (type_in_tuple(Py_TYPE(v), null_types_tuple))
        Py_RETURN_FALSE;
    Py_RETURN_TRUE;
}


static PyObject *
speedups_is_missing(PyObject *self, PyObject *v)
{
    int r = PyObject_IsInstance(v, missing_types_tuple);
    if (r < 0)
        return NULL;
    if (!r)
        Py_RETURN_FALSE;
    r = PyObject_IsTrue(v);
    if (r < 0)
        return NULL;
    if (r)
        Py_RETURN_FALSE;
    Py_RETURN_TRUE;
}


static PyObject *speedups_from_data(PyObject *self, PyObject *v);


static PyObject *
c_to_data(PyObject *v)
{
    PyTypeObject *t = Py_TYPE(v);

    if (t == &PyDict_Type || (PyObject *)t == OrderedDictClass)
        return new_store(DataClass, v);
    if (v == Py_None) {
        Py_INCREF(NullSingleton);
        return NullSingleton;
    }
    if (t == &PyList_Type || t == &PyTuple_Type)
        return new_store(FlatListClass, v);
    if (type_in_tuple(t, generator_types)) {
        /* list_to_data(list(from_data(vv) for vv in v)) */
        PyObject *item, *converted, *out, *result;
        PyObject *iter = PyObject_GetIter(v);
        if (iter == NULL)
            return NULL;
        out = PyList_New(0);
        if (out == NULL) {
            Py_DECREF(iter);
            return NULL;
        }
        while ((item = PyIter_Next(iter)) != NULL) {
            converted = speedups_from_data(NULL, item);
            Py_DECREF(item);
            if (converted == NULL || PyList_Append(out, converted) < 0) {
                Py_XDECREF(converted);
                Py_DECREF(iter);
                Py_DECREF(out);
                return NULL;
            }
            Py_DECREF(converted);
        }
        Py_DECREF(iter);
        if (PyErr_Occurred()) {
            Py_DECREF(out);
            return NULL;
        }
        result = new_store(FlatListClass, out);
        Py_DECREF(out);
        return result;
    }
    Py_INCREF(v);
    return v;
}


static PyObject *
speedups_to_data(PyObject *self, PyObject *args)
{
    PyObject *v = Py_None;
    if (!PyArg_UnpackTuple(args, "to_data", 0, 1, &v))
        return NULL;
    return c_to_data(v);
}


static PyObject *
speedups_from_data(PyObject *self, PyObject *v)
{
    PyObject *t;
    if (v == Py_None)
        Py_RETURN_NONE;

    t = (PyObject *)Py_TYPE(v);
    if (t == NullTypeClass)
        Py_RETURN_NONE;
    if (t == DataClass || t == FlatListClass) {
        PyObject *d = STORE(v);
        if (d == NULL) {
            PyErr_SetObject(PyExc_AttributeError, slot_str);
            return NULL;
        }
        Py_INCREF(d);
        return d;
    }
    if (t == DataObjectClass)
        return PyObject_GenericGetAttr(v, slot_str);
    if (type_in_tuple((PyTypeObject *)t, generator_types))
        return PyObject_CallFunctionObjArgs(from_data_gen, v, NULL);
    if (t == (PyObject *)&PyFloat_Type) {
        if (isnan(PyFloat_AS_DOUBLE(v)))
            Py_RETURN_NONE;
    }
    Py_INCREF(v);
    return v;
}


static PyObject *
speedups_dict_to_data(PyObject *self, PyObject *d)
{
    return new_store(DataClass, d);
}


static PyObject *
speedups_list_to_data(PyObject *self, PyObject *v)
{
    return new_store(FlatListClass, v);
}


/* ======================= _StoreBase ======================================= */

static int
store_traverse(PyObject *self, visitproc visit, void *arg)
{
    Py_VISIT(STORE(self));
    return 0;
}


static int
store_clear_(PyObject *self)
{
    Py_CLEAR(STORE(self));
    return 0;
}


static void
store_dealloc(PyObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_CLEAR(STORE(self));
    Py_TYPE(self)->tp_free(self);
}


static PyMemberDef store_members[] = {
    {"_internal_value", MEMBER_OBJ_EX, offsetof(StoreObject, store), 0, NULL},
    {NULL},
};


static PyTypeObject StoreBase_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "mo_dots._speedups._StoreBase",
    .tp_basicsize = sizeof(StoreObject),
    .tp_dealloc = store_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_traverse = store_traverse,
    .tp_clear = store_clear_,
    .tp_members = store_members,
    .tp_new = PyType_GenericNew,
};


/* ======================= _DataBase ======================================== */

/* WRAP A VALUE FOUND UNDER name IN d; MIRRORS datas._getattr_dispatch */
static PyObject *
wrap_attr_value(PyObject *v, PyObject *d, PyObject *name)
{
    PyTypeObject *t = Py_TYPE(v);

    if (v == Py_None || type_in_tuple(t, null_types_tuple)) {
        if (NullTypeClass == NULL) {
            Py_INCREF(v); /* IMPORT WINDOW: BEHAVE LIKE AN EMPTY DISPATCH */
            return v;
        }
        return new_null(d, name);
    }
    if (t == &PyDict_Type || (PyObject *)t == OrderedDictClass) {
        if (DataClass == NULL) {
            Py_INCREF(v);
            return v;
        }
        return new_store(DataClass, v);
    }
    if (t == &PyList_Type) {
        if (FlatListClass == NULL) {
            Py_INCREF(v);
            return v;
        }
        return new_store(FlatListClass, v);
    }
    if (type_in_tuple(t, generator_types) && from_data_gen != NULL) {
        PyObject *out, *lst = PySequence_List(v);
        if (lst == NULL)
            return NULL;
        {
            Py_ssize_t i, n = PyList_GET_SIZE(lst);
            for (i = 0; i < n; i++) {
                PyObject *conv = speedups_from_data(NULL, PyList_GET_ITEM(lst, i));
                if (conv == NULL) {
                    Py_DECREF(lst);
                    return NULL;
                }
                PyList_SetItem(lst, i, conv);
            }
        }
        out = new_store(FlatListClass, lst);
        Py_DECREF(lst);
        return out;
    }
    Py_INCREF(v);
    return v;
}


static PyObject *
data_getattro(PyObject *self, PyObject *name)
{
    int found;
    PyObject *d, *v;
    PyObject *attr = bind_type_attr(self, name, &found);
    if (found)
        return attr; /* MAY BE NULL ON ERROR */

    d = STORE(self);
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, name);
        return NULL;
    }
    if (PyDict_CheckExact(d)) {
        v = PyDict_GetItemWithError(d, name); /* borrowed */
        if (v == NULL) {
            if (PyErr_Occurred())
                return NULL;
            if (NullTypeClass == NULL)
                Py_RETURN_NONE; /* IMPORT WINDOW: d.get(key) IS None */
            return new_null(d, name);
        }
        return wrap_attr_value(v, d, name);
    }
    /* NON-dict SLOT: ORIGINAL PYTHON __getattr__ (MAY RAISE, AS BEFORE) */
    return PyObject_CallFunctionObjArgs(data_getattr_slow, self, name, NULL);
}


static int
data_setattro(PyObject *self, PyObject *name, PyObject *value)
{
    PyObject *d = STORE(self);
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, name);
        return -1;
    }

    if (value == NULL) {
        /* __delattr__: d.pop(key, None) */
        if (PyDict_CheckExact(d)) {
            if (PyDict_DelItem(d, name) < 0) {
                if (!PyErr_ExceptionMatches(PyExc_KeyError))
                    return -1;
                PyErr_Clear();
            }
            return 0;
        }
        {
            PyObject *r = PyObject_CallMethod(d, "pop", "OO", name, Py_None);
            if (r == NULL)
                return -1;
            Py_DECREF(r);
            return 0;
        }
    }

    {
        PyObject *unwrapped = speedups_from_data(NULL, value);
        int rc;
        if (unwrapped == NULL)
            return -1;
        if (unwrapped == Py_None) {
            Py_DECREF(unwrapped);
            if (PyDict_CheckExact(d)) {
                if (PyDict_DelItem(d, name) < 0) {
                    if (!PyErr_ExceptionMatches(PyExc_KeyError))
                        return -1;
                    PyErr_Clear();
                }
                return 0;
            }
            {
                PyObject *r = PyObject_CallMethod(d, "pop", "OO", name, Py_None);
                if (r == NULL)
                    return -1;
                Py_DECREF(r);
                return 0;
            }
        }
        if (PyDict_CheckExact(d))
            rc = PyDict_SetItem(d, name, unwrapped);
        else
            rc = PyObject_SetItem(d, name, unwrapped);
        Py_DECREF(unwrapped);
        return rc;
    }
}


/* _getdefault FALLS BACK TO obj[int(seg)] ON A dict MISS WHEN seg PARSES AS
 * float; ANY SEGMENT THAT COULD PARSE SENDS THE WALK TO PURE PYTHON */
static int
numeric_candidate(PyObject *seg)
{
    Py_ssize_t i, len = PyUnicode_GET_LENGTH(seg);
    if (len == 0)
        return 1;
    for (i = 0; i < len; i++) {
        Py_UCS4 c = PyUnicode_READ_CHAR(seg, i);
        if ((c >= '0' && c <= '9') || c == '.' || c == '+' || c == '-' || c == 'e' || c == 'E'
            || c == '_' || c <= ' ')
            continue;
        return 0;
    }
    return 1;
}


/* THE DOTTED WALK OF Data.__getitem__; RETURNS NULL WITH NO ERROR SET TO BAIL */
static PyObject *
dotted_walk(PyObject *d, PyObject *key)
{
    PyObject *segments, *cur, *result;
    Py_ssize_t i, n;
    Py_ssize_t len = PyUnicode_GET_LENGTH(key);

    if (PyUnicode_FindChar(key, '\b', 0, len, 1) >= 0)
        return NULL; /* ESCAPED-DOT KEYS: PURE */
    segments = PyUnicode_Split(key, dot_str, -1);
    if (segments == NULL)
        return NULL; /* ERROR SET; CALLER BAILS TO PURE WHICH RE-RAISES */
    n = PyList_GET_SIZE(segments);
    for (i = 0; i < n; i++) {
        /* EMPTY SEGMENT MEANS "." ITSELF, A LEADING/TRAILING DOT, OR ".." */
        if (PyUnicode_GET_LENGTH(PyList_GET_ITEM(segments, i)) == 0) {
            Py_DECREF(segments);
            return NULL;
        }
    }

    cur = d;
    Py_INCREF(cur);
    for (i = 0; i < n; i++) {
        PyObject *seg = PyList_GET_ITEM(segments, i); /* borrowed */
        PyObject *next;
        if ((PyObject *)Py_TYPE(cur) == NullTypeClass) {
            next = new_null(cur, seg);
            if (next == NULL)
                goto error;
        }
        else if (PyDict_CheckExact(cur)) {
            next = PyDict_GetItemWithError(cur, seg); /* borrowed */
            if (next == NULL) {
                if (PyErr_Occurred())
                    goto error;
                if (numeric_candidate(seg))
                    goto bail; /* MAY BE AN int KEY: PURE _getdefault DECIDES */
                next = new_null(cur, seg);
                if (next == NULL)
                    goto error;
            }
            else {
                if (next == Py_None && i + 1 < n)
                    goto bail; /* None MID-WALK: PURE _getdefault SEMANTICS */
                Py_INCREF(next);
            }
        }
        else {
            goto bail; /* is_many, None, DataObject, ...: PURE */
        }
        Py_DECREF(cur);
        cur = next;
    }
    Py_DECREF(segments);
    result = c_to_data(cur);
    Py_DECREF(cur);
    return result;

bail:
    Py_DECREF(segments);
    Py_DECREF(cur);
    return NULL; /* NO ERROR SET */
error:
    Py_DECREF(segments);
    Py_DECREF(cur);
    return NULL; /* ERROR SET */
}


static PyObject *
data_subscript(PyObject *self, PyObject *key)
{
    if (PyUnicode_CheckExact(key)) {
        Py_ssize_t len = PyUnicode_GET_LENGTH(key);
        PyObject *d = STORE(self);
        if (d != NULL) {
            if (PyUnicode_FindChar(key, '.', 0, len, 1) < 0) {
                if (PyDict_CheckExact(d)) {
                    PyObject *v = PyDict_GetItemWithError(d, key); /* borrowed */
                    if (v == NULL) {
                        if (PyErr_Occurred())
                            return NULL;
                        return new_null(d, key);
                    }
                    if (v == Py_None || type_in_tuple(Py_TYPE(v), null_types_tuple))
                        return new_null(d, key);
                    return c_to_data(v);
                }
            }
            else if (len > 1) {
                PyObject *r = dotted_walk(d, key);
                if (r != NULL)
                    return r;
                if (PyErr_Occurred())
                    return NULL;
                /* BAILED: FALL THROUGH TO PURE */
            }
        }
    }
    /* DOTTED EDGE CASES, ".", NON-str KEYS, NON-dict SLOTS: ORIGINAL PYTHON */
    return PyObject_CallFunctionObjArgs(data_getitem_slow, self, key, NULL);
}


static int
data_bool(PyObject *self)
{
    PyObject *d = STORE(self);
    PyObject *r;
    int t;
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, slot_str);
        return -1;
    }
    if (PyDict_CheckExact(d))
        return 1;
    r = PyObject_RichCompare(d, Py_None, Py_NE);
    if (r == NULL)
        return -1;
    t = PyObject_IsTrue(r);
    Py_DECREF(r);
    return t;
}


static int
data_ass_subscript(PyObject *self, PyObject *key, PyObject *value)
{
    PyObject *r;
    if (PyUnicode_CheckExact(key)) {
        Py_ssize_t len = PyUnicode_GET_LENGTH(key);
        if (len > 0 && PyUnicode_FindChar(key, '.', 0, len, 1) < 0) {
            PyObject *d = STORE(self);
            if (d != NULL && PyDict_CheckExact(d)) {
                if (value == NULL) {
                    /* __delitem__: d.pop(key, None) */
                    if (PyDict_DelItem(d, key) < 0) {
                        if (!PyErr_ExceptionMatches(PyExc_KeyError))
                            return -1;
                        PyErr_Clear();
                    }
                    return 0;
                }
                {
                    PyObject *unwrapped = speedups_from_data(NULL, value);
                    int rc;
                    if (unwrapped == NULL)
                        return -1;
                    if (unwrapped == Py_None) {
                        Py_DECREF(unwrapped);
                        if (PyDict_DelItem(d, key) < 0) {
                            if (!PyErr_ExceptionMatches(PyExc_KeyError))
                                return -1;
                            PyErr_Clear();
                        }
                        return 0;
                    }
                    rc = PyDict_SetItem(d, key, unwrapped);
                    Py_DECREF(unwrapped);
                    return rc;
                }
            }
        }
    }
    /* DOTTED KEYS, ".", "", NON-str KEYS, NON-dict SLOTS: ORIGINAL PYTHON */
    if (value == NULL)
        r = PyObject_CallFunctionObjArgs(data_delitem_slow, self, key, NULL);
    else
        r = PyObject_CallFunctionObjArgs(data_setitem_slow, self, key, value, NULL);
    if (r == NULL)
        return -1;
    Py_DECREF(r);
    return 0;
}


static PyObject *
databs_get(PyObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"key", "default", NULL};
    PyObject *key, *dflt = NULL, *v;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O", kwlist, &key, &dflt))
        return NULL;
    if (dflt == NULL)
        dflt = NullSingleton;
    v = PyObject_GetItem(self, key);
    if (v == NULL)
        return NULL;
    if ((PyObject *)Py_TYPE(v) == NullTypeClass) {
        Py_DECREF(v);
        if (dflt == NullSingleton)
            return new_null(self, key);
        Py_INCREF(dflt);
        return dflt;
    }
    return v;
}


static PyObject *
databs_items(PyObject *self, PyObject *unused)
{
    PyObject *d = STORE(self);
    PyObject *out, *k, *v;
    Py_ssize_t pos = 0;
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, slot_str);
        return NULL;
    }
    if (!PyDict_CheckExact(d))
        return PyObject_CallFunctionObjArgs(data_items_slow, self, NULL);

    out = PyList_New(0);
    if (out == NULL)
        return NULL;
    while (PyDict_Next(d, &pos, &k, &v)) {
        int keep;
        PyTypeObject *t = Py_TYPE(v);
        if (v == Py_None || type_in_tuple(t, null_types_tuple))
            keep = 0;
        else if (t == &PyDict_Type || t == &PyUnicode_Type || t == &PyLong_Type
                 || t == &PyFloat_Type || t == &PyList_Type || t == &PyBool_Type)
            keep = 1;
        else {
            /* KEEP IF v != None IS TRUTHY, ELSE IF is_data(v) */
            PyObject *r = PyObject_RichCompare(v, Py_None, Py_NE);
            if (r == NULL)
                goto error;
            keep = PyObject_IsTrue(r);
            Py_DECREF(r);
            if (keep < 0)
                goto error;
            if (!keep)
                keep = type_in_tuple(t, data_types_tuple);
        }
        if (keep) {
            PyObject *wrapped = c_to_data(v);
            PyObject *pair;
            if (wrapped == NULL)
                goto error;
            pair = PyTuple_Pack(2, k, wrapped);
            Py_DECREF(wrapped);
            if (pair == NULL)
                goto error;
            if (PyList_Append(out, pair) < 0) {
                Py_DECREF(pair);
                goto error;
            }
            Py_DECREF(pair);
        }
    }
    return out;
error:
    Py_DECREF(out);
    return NULL;
}


static PyObject *
data_iter(PyObject *self)
{
    PyObject *d = STORE(self);
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, slot_str);
        return NULL;
    }
    if (PyDict_CheckExact(d)) {
        /* yield from d.items(): ITERATE THE LIVE VIEW */
        PyObject *it, *items = PyObject_CallMethod(d, "items", NULL);
        if (items == NULL)
            return NULL;
        it = PyObject_GetIter(items);
        Py_DECREF(items);
        return it;
    }
    return PyObject_GetIter(d);
}


static int
data_contains(PyObject *self, PyObject *key)
{
    /* is_data(self[key]) or bool(self[key]) */
    int r;
    PyObject *v = data_subscript(self, key);
    if (v == NULL)
        return -1;
    if (type_in_tuple(Py_TYPE(v), data_types_tuple))
        r = 1;
    else
        r = PyObject_IsTrue(v);
    Py_DECREF(v);
    return r;
}


static Py_ssize_t
data_length(PyObject *self)
{
    PyObject *d = STORE(self);
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, slot_str);
        return -1;
    }
    if (!PyDict_Check(d)) {
        /* PURE CALLS dict.__len__(d): SAME TypeError ON A NON-dict SLOT */
        PyErr_Format(
            PyExc_TypeError,
            "descriptor '__len__' requires a 'dict' object but received a '%s'",
            Py_TYPE(d)->tp_name);
        return -1;
    }
    return PyDict_Size(d);
}


static PyMethodDef data_methods[] = {
    {"get", (PyCFunction)(void (*)(void))databs_get, METH_VARARGS | METH_KEYWORDS,
     "get(key, default=Null) - value at key, wrapped; default on miss"},
    {"items", databs_items, METH_NOARGS, "[(key, to_data(value))] with null values dropped"},
    {NULL, NULL, 0, NULL},
};


static PyNumberMethods data_as_number = {
    .nb_bool = data_bool,
};

static PyMappingMethods data_as_mapping = {
    .mp_length = data_length,
    .mp_subscript = data_subscript,
    .mp_ass_subscript = data_ass_subscript,
};

static PySequenceMethods data_as_sequence = {
    .sq_contains = data_contains,
};


static PyTypeObject DataBase_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "mo_dots._speedups._DataBase",
    .tp_basicsize = sizeof(StoreObject),
    .tp_dealloc = store_dealloc,
    .tp_getattro = data_getattro,
    .tp_setattro = data_setattro,
    .tp_iter = data_iter,
    .tp_as_number = &data_as_number,
    .tp_as_sequence = &data_as_sequence,
    .tp_as_mapping = &data_as_mapping,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_traverse = store_traverse,
    .tp_clear = store_clear_,
    .tp_methods = data_methods,
    .tp_base = &StoreBase_Type,
};


/* ======================= _NullBase ======================================== */

static int
nullb_traverse(PyObject *self, visitproc visit, void *arg)
{
    Py_VISIT(STORE(self));
    Py_VISIT(NKEY(self));
    return 0;
}


static int
nullb_clear_(PyObject *self)
{
    Py_CLEAR(STORE(self));
    Py_CLEAR(NKEY(self));
    return 0;
}


static void
nullb_dealloc(PyObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_CLEAR(STORE(self));
    Py_CLEAR(NKEY(self));
    Py_TYPE(self)->tp_free(self);
}


static int
nullb_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"obj", "key", NULL};
    PyObject *obj = Py_None, *key = Py_None;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OO", kwlist, &obj, &key))
        return -1;
    Py_INCREF(obj);
    Py_XSETREF(STORE(self), obj);
    Py_INCREF(key);
    Py_XSETREF(NKEY(self), key);
    return 0;
}


static PyObject *
return_null(void)
{
    if (NullSingleton == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "mo_dots._speedups not initialized");
        return NULL;
    }
    Py_INCREF(NullSingleton);
    return NullSingleton;
}


static PyObject *
nullb_getattro(PyObject *self, PyObject *name)
{
    int found;
    PyObject *o;
    PyObject *attr = bind_type_attr(self, name, &found);
    if (found)
        return attr;

    o = STORE(self);
    if (o == NULL || o == Py_None || o == NullSingleton)
        return return_null(); /* DEAD CHAIN */

    if (PyDict_CheckExact(o) && NKEY(self) != NULL && PyUnicode_CheckExact(NKEY(self))) {
        PyObject *v = PyDict_GetItemWithError(o, NKEY(self)); /* borrowed */
        if (v == NULL) {
            if (PyErr_Occurred())
                return NULL;
            return new_null(self, name);
        }
        if (v == Py_None || type_in_tuple(Py_TYPE(v), null_types_tuple))
            return new_null(self, name);
        /* VALUE MATERIALIZED SINCE: FALL THROUGH TO PYTHON */
    }
    else if ((PyObject *)Py_TYPE(o) == NullTypeClass) {
        return new_null(self, name); /* LIVE NullType CHAIN */
    }
    return PyObject_CallFunctionObjArgs(null_getattr_slow, self, name, NULL);
}


static PyObject *
nullb_subscript(PyObject *self, PyObject *key)
{
    PyObject *o;
    if (PySlice_Check(key))
        return return_null();
    o = STORE(self);
    if (o == NULL || o == Py_None || o == NullSingleton)
        return return_null(); /* DEAD CHAIN */
    if (PyLong_CheckExact(key))
        return new_null(self, key);
    if (PyUnicode_CheckExact(key)) {
        Py_ssize_t len = PyUnicode_GET_LENGTH(key);
        if (PyUnicode_FindChar(key, '.', 0, len, 1) < 0
            && PyUnicode_FindChar(key, '\b', 0, len, 1) < 0) {
            return new_null(self, key);
        }
    }
    return PyObject_CallFunctionObjArgs(null_getitem_slow, self, key, NULL);
}


static Py_ssize_t
nullb_length(PyObject *self)
{
    return 0;
}


static int
nullb_bool(PyObject *self)
{
    return 0;
}


static PyObject *
nullb_richcompare(PyObject *self, PyObject *other, int op)
{
    int r;
    switch (op) {
    case Py_EQ:
        r = PyObject_IsInstance(other, sequence_types_tuple);
        if (r < 0)
            return NULL;
        if (r) {
            r = PyObject_IsTrue(other);
            if (r < 0)
                return NULL;
            if (!r)
                Py_RETURN_TRUE;
        }
        if (type_in_tuple(Py_TYPE(other), null_types_tuple))
            Py_RETURN_TRUE;
        return return_null();
    case Py_NE: {
        PyObject *m = speedups_is_missing(NULL, other);
        if (m == NULL)
            return NULL;
        r = (m == Py_True);
        Py_DECREF(m);
        if (r)
            Py_RETURN_FALSE;
        return return_null();
    }
    default:
        return return_null();
    }
}


/* BINARY SLOTS RECEIVE (a, b) WITH OUR INSTANCE ON EITHER SIDE */
static inline PyObject *
other_operand(PyObject *a, PyObject *b)
{
    return type_in_tuple(Py_TYPE(a), null_types_tuple) ? b : a;
}


static PyObject *
nullb_add(PyObject *a, PyObject *b)
{
    PyObject *other = other_operand(a, b);
    int r = PyObject_IsInstance(other, sequence_types_tuple);
    if (r < 0)
        return NULL;
    if (r) {
        Py_INCREF(other);
        return other;
    }
    return return_null();
}


static PyObject *
nullb_null_result(PyObject *a, PyObject *b)
{
    return return_null();
}


static PyObject *
nullb_negative(PyObject *self)
{
    return return_null();
}


static PyObject *
nullb_or(PyObject *a, PyObject *b)
{
    PyObject *other = other_operand(a, b);
    Py_INCREF(other);
    return other;
}


static PyObject *
nullb_and(PyObject *a, PyObject *b)
{
    PyObject *other = other_operand(a, b);
    if (other == Py_False)
        Py_RETURN_FALSE;
    return return_null();
}


static PyObject *
nullb_int(PyObject *self)
{
    /* PURE __int__ RETURNS None; CPython THEN RAISES THE SAME TypeError */
    Py_RETURN_NONE;
}


static PyObject *
nullb_float(PyObject *self)
{
    return PyFloat_FromDouble(Py_NAN);
}


static PyObject *
nullb_iter(PyObject *self)
{
    return PyObject_GetIter(empty_tuple);
}


static PyObject *
nullb_call(PyObject *self, PyObject *args, PyObject *kwds)
{
    return return_null();
}


static Py_hash_t
nullb_hash(PyObject *self)
{
    return null_hash;
}


static PyObject *
nullb_str(PyObject *self)
{
    Py_INCREF(empty_str);
    return empty_str;
}


static PyObject *
nullb_repr(PyObject *self)
{
    Py_INCREF(null_repr_str);
    return null_repr_str;
}


static PyNumberMethods null_as_number = {
    .nb_add = nullb_add,
    .nb_subtract = nullb_null_result,
    .nb_multiply = nullb_null_result,
    .nb_bool = nullb_bool,
    .nb_negative = nullb_negative,
    .nb_and = nullb_and,
    .nb_xor = nullb_null_result,
    .nb_or = nullb_or,
    .nb_int = nullb_int,
    .nb_float = nullb_float,
    .nb_floor_divide = nullb_null_result,
    .nb_true_divide = nullb_null_result,
    .nb_inplace_true_divide = nullb_null_result,
};

static PyMappingMethods null_as_mapping = {
    .mp_length = nullb_length,
    .mp_subscript = nullb_subscript,
};

static PyMemberDef null_members[] = {
    {"_internal_value", MEMBER_OBJ_EX, offsetof(NullObject, store), 0, NULL},
    {"_key", MEMBER_OBJ_EX, offsetof(NullObject, key), 0, NULL},
    {NULL},
};


static PyTypeObject NullBase_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "mo_dots._speedups._NullBase",
    .tp_basicsize = sizeof(NullObject),
    .tp_dealloc = nullb_dealloc,
    .tp_repr = nullb_repr,
    .tp_as_number = &null_as_number,
    .tp_as_mapping = &null_as_mapping,
    .tp_hash = nullb_hash,
    .tp_call = nullb_call,
    .tp_str = nullb_str,
    .tp_getattro = nullb_getattro,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_traverse = nullb_traverse,
    .tp_clear = nullb_clear_,
    .tp_richcompare = nullb_richcompare,
    .tp_iter = nullb_iter,
    .tp_init = nullb_init,
    .tp_members = null_members,
    .tp_new = PyType_GenericNew,
};


/* ======================= _ListBase ======================================== */

/* APPEND THE COLUMN VALUE FOR ONE RAW dict-VALUE; 0 OK, -1 ERROR, 1 BAIL */
static int
flat_classify_append(PyObject *out, PyObject *raw)
{
    PyTypeObject *t = Py_TYPE(raw);

    if (raw == Py_None || type_in_tuple(t, null_types_tuple))
        return 0; /* SKIPPED */
    if (t == &PyFloat_Type) {
        if (isnan(PyFloat_AS_DOUBLE(raw)))
            return 0; /* from_data(nan) IS None */
        return PyList_Append(out, raw);
    }
    if (t == &PyUnicode_Type) {
        if (PyUnicode_GET_LENGTH(raw) == 0)
            return 0; /* is_missing("") */
        return PyList_Append(out, raw);
    }
    if (t == &PyList_Type || t == &PyTuple_Type) {
        /* is_missing(EMPTY) SKIPS; is_many EXTENDS RAW ITEMS */
        Py_ssize_t i, n = PySequence_Fast_GET_SIZE(raw);
        for (i = 0; i < n; i++) {
            if (PyList_Append(out, PySequence_Fast_GET_ITEM(raw, i)) < 0)
                return -1;
        }
        return 0;
    }
    if (t == &PyDict_Type || t == &PyLong_Type || t == &PyBool_Type)
        return PyList_Append(out, raw);
    if ((PyObject *)t == DataClass || (PyObject *)t == FlatListClass) {
        /* from_data FIRST: THE SLOT RIDES IN */
        PyObject *slot = STORE(raw);
        if (slot == NULL)
            return 1;
        return flat_classify_append(out, slot);
    }
    if (type_in_tuple(t, generator_types))
        return 1; /* PURE from_data-MAPS THE ITEMS */
    {
        /* GENERIC: is_missing -> SKIP; is_many -> EXTEND; ELSE APPEND */
        int r = PyObject_IsInstance(raw, missing_types_tuple);
        if (r < 0)
            return -1;
        if (r) {
            r = PyObject_IsTrue(raw);
            if (r < 0)
                return -1;
            if (!r)
                return 0;
        }
        r = PyObject_IsInstance(raw, many_types_tuple);
        if (r < 0)
            return -1;
        if (r) {
            PyObject *item, *iter = PyObject_GetIter(raw);
            if (iter == NULL)
                return -1;
            while ((item = PyIter_Next(iter)) != NULL) {
                if (PyList_Append(out, item) < 0) {
                    Py_DECREF(item);
                    Py_DECREF(iter);
                    return -1;
                }
                Py_DECREF(item);
            }
            Py_DECREF(iter);
            return PyErr_Occurred() ? -1 : 0;
        }
        return PyList_Append(out, raw);
    }
}


/* FlatList.get(key) COLUMN EXTRACT; RETURNS NULL WITH NO ERROR SET TO BAIL */
static PyObject *
flatlist_get_impl(PyObject *self, PyObject *key)
{
    PyObject *d, *out, *result;
    Py_ssize_t i, n, len;

    if (!PyUnicode_CheckExact(key))
        return NULL;
    len = PyUnicode_GET_LENGTH(key);
    if (len == 0 || PyUnicode_FindChar(key, '.', 0, len, 1) >= 0
        || PyUnicode_FindChar(key, '\b', 0, len, 1) >= 0 || numeric_candidate(key))
        return NULL; /* ".", DOTTED, ESCAPED, obj[int(key)] CANDIDATES: PURE */
    if (DataClass == NULL)
        return NULL;
    {
        /* A Data TYPE ATTR SHADOWS THE dict VALUE PER ELEMENT: PURE */
        PyObject *descr = mro_lookup((PyTypeObject *)DataClass, key);
        if (descr != NULL) {
            Py_DECREF(descr);
            return NULL;
        }
        if (PyErr_Occurred())
            return NULL;
    }
    d = STORE(self);
    if (d == NULL || !PyList_CheckExact(d))
        return NULL;

    out = PyList_New(0);
    if (out == NULL)
        return NULL;
    n = PyList_GET_SIZE(d);
    for (i = 0; i < n; i++) {
        PyObject *v = PyList_GET_ITEM(d, i);
        if (v == Py_None)
            continue; /* Null NAVIGATION ANSWERS None: SKIPPED */
        if (!PyDict_CheckExact(v))
            goto bail; /* OBJECTS, NESTED LISTS, ...: PURE */
        {
            PyObject *raw = PyDict_GetItemWithError(v, key); /* borrowed */
            int rc;
            if (raw == NULL) {
                if (PyErr_Occurred())
                    goto error;
                continue;
            }
            rc = flat_classify_append(out, raw);
            if (rc < 0)
                goto error;
            if (rc > 0)
                goto bail;
        }
    }
    result = new_store(FlatListClass, out);
    Py_DECREF(out);
    return result;

bail:
    Py_DECREF(out);
    PyErr_Clear();
    return NULL; /* NO ERROR SET */
error:
    Py_DECREF(out);
    return NULL; /* ERROR SET */
}


static PyObject *
flatlist_getattro(PyObject *self, PyObject *name)
{
    int found;
    PyObject *r;
    PyObject *attr = bind_type_attr(self, name, &found);
    if (found)
        return attr;

    {
        int eq = PyObject_RichCompareBool(name, json_str, Py_EQ);
        if (eq < 0)
            return NULL;
        if (!eq) {
            eq = PyObject_RichCompareBool(name, call_str, Py_EQ);
            if (eq < 0)
                return NULL;
        }
        if (eq) {
            PyErr_SetObject(PyExc_AttributeError, name);
            return NULL;
        }
    }

    r = flatlist_get_impl(self, name);
    if (r != NULL)
        return r;
    if (PyErr_Occurred())
        return NULL;
    return PyObject_CallFunctionObjArgs(flatlist_get_slow, self, name, NULL);
}


static PyObject *
listbs_get(PyObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"key", NULL};
    PyObject *key, *r;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O", kwlist, &key))
        return NULL;
    r = flatlist_get_impl(self, key);
    if (r != NULL)
        return r;
    if (PyErr_Occurred())
        return NULL;
    return PyObject_CallFunctionObjArgs(flatlist_get_slow, self, key, NULL);
}


static PyObject *
list_iter(PyObject *self)
{
    /* iter([to_data(v) for v in slot]) */
    PyObject *d = STORE(self);
    PyObject *out, *it;
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, slot_str);
        return NULL;
    }
    if (PyList_CheckExact(d) || PyTuple_CheckExact(d)) {
        Py_ssize_t i, n = PySequence_Fast_GET_SIZE(d);
        out = PyList_New(n);
        if (out == NULL)
            return NULL;
        for (i = 0; i < n; i++) {
            PyObject *w = c_to_data(PySequence_Fast_GET_ITEM(d, i));
            if (w == NULL) {
                Py_DECREF(out);
                return NULL;
            }
            PyList_SET_ITEM(out, i, w);
        }
    }
    else {
        PyObject *item, *src = PyObject_GetIter(d);
        if (src == NULL)
            return NULL;
        out = PyList_New(0);
        if (out == NULL) {
            Py_DECREF(src);
            return NULL;
        }
        while ((item = PyIter_Next(src)) != NULL) {
            PyObject *w = c_to_data(item);
            Py_DECREF(item);
            if (w == NULL || PyList_Append(out, w) < 0) {
                Py_XDECREF(w);
                Py_DECREF(src);
                Py_DECREF(out);
                return NULL;
            }
            Py_DECREF(w);
        }
        Py_DECREF(src);
        if (PyErr_Occurred()) {
            Py_DECREF(out);
            return NULL;
        }
    }
    it = PyObject_GetIter(out);
    Py_DECREF(out);
    return it;
}


static int
list_contains(PyObject *self, PyObject *item)
{
    PyObject *d = STORE(self);
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, slot_str);
        return -1;
    }
    if (PyList_CheckExact(d))
        return PySequence_Contains(d, item);
    {
        /* PURE CALLS list.__contains__(slot, item): SAME TypeError ON NON-list */
        int t;
        PyObject *r = PyObject_CallFunctionObjArgs(list_contains_meth, d, item, NULL);
        if (r == NULL)
            return -1;
        t = PyObject_IsTrue(r);
        Py_DECREF(r);
        return t;
    }
}


static Py_ssize_t
list_length(PyObject *self)
{
    PyObject *d = STORE(self);
    if (d == NULL) {
        PyErr_SetObject(PyExc_AttributeError, slot_str);
        return -1;
    }
    if (PyList_CheckExact(d))
        return PyList_GET_SIZE(d);
    return PyObject_Size(d);
}


static PyMethodDef list_methods[] = {
    {"get", (PyCFunction)(void (*)(void))listbs_get, METH_VARARGS | METH_KEYWORDS,
     "get(key) - column extract: value at key for each element, nulls dropped, lists flattened"},
    {NULL, NULL, 0, NULL},
};


static PySequenceMethods list_as_sequence = {
    .sq_length = list_length,
    .sq_contains = list_contains,
};


static PyTypeObject ListBase_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "mo_dots._speedups._ListBase",
    .tp_basicsize = sizeof(StoreObject),
    .tp_dealloc = store_dealloc,
    .tp_getattro = flatlist_getattro,
    .tp_iter = list_iter,
    .tp_as_sequence = &list_as_sequence,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_traverse = store_traverse,
    .tp_clear = store_clear_,
    .tp_methods = list_methods,
    .tp_base = &StoreBase_Type,
};


/* ======================= WIRING =========================================== */

static PyObject *
speedups_sync(PyObject *self, PyObject *args)
{
    PyObject *nulls, *missings, *sequences, *datas, *manys;
    if (!PyArg_ParseTuple(
            args, "O!O!O!O!O!",
            &PyTuple_Type, &nulls, &PyTuple_Type, &missings, &PyTuple_Type, &sequences,
            &PyTuple_Type, &datas, &PyTuple_Type, &manys))
        return NULL;
    Py_INCREF(nulls);
    Py_XSETREF(null_types_tuple, nulls);
    Py_INCREF(missings);
    Py_XSETREF(missing_types_tuple, missings);
    Py_INCREF(sequences);
    Py_XSETREF(sequence_types_tuple, sequences);
    Py_INCREF(datas);
    Py_XSETREF(data_types_tuple, datas);
    Py_INCREF(manys);
    Py_XSETREF(many_types_tuple, manys);
    Py_RETURN_NONE;
}


static PyObject *
speedups_init_null(PyObject *self, PyObject *args)
{
    PyObject *cls, *getattr_slow, *getitem_slow;
    if (!PyArg_ParseTuple(args, "OOO", &cls, &getattr_slow, &getitem_slow))
        return NULL;
    if (!PyType_Check(cls) || !PyType_IsSubtype((PyTypeObject *)cls, &NullBase_Type)) {
        PyErr_SetString(PyExc_TypeError, "expected a _NullBase subclass");
        return NULL;
    }
    Py_INCREF(cls);
    Py_XSETREF(NullTypeClass, cls);
    Py_INCREF(getattr_slow);
    Py_XSETREF(null_getattr_slow, getattr_slow);
    Py_INCREF(getitem_slow);
    Py_XSETREF(null_getitem_slow, getitem_slow);
    Py_RETURN_NONE;
}


static PyObject *
speedups_set_null(PyObject *self, PyObject *null_)
{
    Py_INCREF(null_);
    Py_XSETREF(NullSingleton, null_);
    Py_RETURN_NONE;
}


static PyObject *
speedups_init_data(PyObject *self, PyObject *args)
{
    PyObject *cls, *getattr_slow, *getitem_slow, *setitem_slow, *delitem_slow, *items_slow;
    if (!PyArg_ParseTuple(
            args, "OOOOOO",
            &cls, &getattr_slow, &getitem_slow, &setitem_slow, &delitem_slow, &items_slow))
        return NULL;
    if (!PyType_Check(cls) || !PyType_IsSubtype((PyTypeObject *)cls, &StoreBase_Type)) {
        PyErr_SetString(PyExc_TypeError, "expected a _StoreBase subclass");
        return NULL;
    }
    Py_INCREF(cls);
    Py_XSETREF(DataClass, cls);
    Py_INCREF(getattr_slow);
    Py_XSETREF(data_getattr_slow, getattr_slow);
    Py_INCREF(getitem_slow);
    Py_XSETREF(data_getitem_slow, getitem_slow);
    Py_INCREF(setitem_slow);
    Py_XSETREF(data_setitem_slow, setitem_slow);
    Py_INCREF(delitem_slow);
    Py_XSETREF(data_delitem_slow, delitem_slow);
    Py_INCREF(items_slow);
    Py_XSETREF(data_items_slow, items_slow);
    Py_RETURN_NONE;
}


static PyObject *
speedups_init_list(PyObject *self, PyObject *args)
{
    PyObject *cls, *get_slow;
    if (!PyArg_ParseTuple(args, "OO", &cls, &get_slow))
        return NULL;
    if (!PyType_Check(cls) || !PyType_IsSubtype((PyTypeObject *)cls, &StoreBase_Type)) {
        PyErr_SetString(PyExc_TypeError, "expected a _StoreBase subclass");
        return NULL;
    }
    Py_INCREF(cls);
    Py_XSETREF(FlatListClass, cls);
    Py_INCREF(get_slow);
    Py_XSETREF(flatlist_get_slow, get_slow);
    Py_RETURN_NONE;
}


static PyObject *
speedups_init(PyObject *self, PyObject *args)
{
    PyObject *data, *flat, *nulltype, *null_, *dataobject, *odict, *gens, *gen_helper;
    if (!PyArg_ParseTuple(
            args, "OOOOOOO!O",
            &data, &flat, &nulltype, &null_, &dataobject, &odict,
            &PyTuple_Type, &gens, &gen_helper))
        return NULL;

    if (!PyType_Check(data) || !PyType_IsSubtype((PyTypeObject *)data, &StoreBase_Type)
        || !PyType_Check(flat) || !PyType_IsSubtype((PyTypeObject *)flat, &StoreBase_Type)
        || !PyType_Check(nulltype) || !PyType_IsSubtype((PyTypeObject *)nulltype, &NullBase_Type)) {
        PyErr_SetString(PyExc_TypeError, "expected rebuilt C-backed classes");
        return NULL;
    }

    Py_INCREF(data);
    Py_XSETREF(DataClass, data);
    Py_INCREF(flat);
    Py_XSETREF(FlatListClass, flat);
    Py_INCREF(nulltype);
    Py_XSETREF(NullTypeClass, nulltype);
    Py_INCREF(null_);
    Py_XSETREF(NullSingleton, null_);
    Py_INCREF(dataobject);
    Py_XSETREF(DataObjectClass, dataobject);
    Py_INCREF(odict);
    Py_XSETREF(OrderedDictClass, odict);
    Py_INCREF(gens);
    Py_XSETREF(generator_types, gens);
    Py_INCREF(gen_helper);
    Py_XSETREF(from_data_gen, gen_helper);
    Py_RETURN_NONE;
}


static PyMethodDef speedups_methods[] = {
    {"is_null", speedups_is_null, METH_O, "True if value is an instance of a registered null type"},
    {"is_not_null", speedups_is_not_null, METH_O, "False if value is an instance of a registered null type"},
    {"is_missing", speedups_is_missing, METH_O, "True if value is effectively nothing"},
    {"to_data", speedups_to_data, METH_VARARGS, "wrap value for null-safe navigation"},
    {"from_data", speedups_from_data, METH_O, "unwrap to the underlying python value"},
    {"dict_to_data", speedups_dict_to_data, METH_O, "wrap dict as Data, no checks"},
    {"list_to_data", speedups_list_to_data, METH_O, "wrap list as FlatList, no checks"},
    {"_sync", speedups_sync, METH_VARARGS, "(null_types, missing_types, sequence_types) - refresh registries"},
    {"_init_null", speedups_init_null, METH_VARARGS, "(NullType, getattr_slow, getitem_slow)"},
    {"_set_null", speedups_set_null, METH_O, "store the Null singleton"},
    {"_init_data", speedups_init_data, METH_VARARGS, "(Data, getattr_slow, getitem_slow)"},
    {"_init_list", speedups_init_list, METH_VARARGS, "(FlatList, get_slow)"},
    {"_init", speedups_init, METH_VARARGS,
     "(Data, FlatList, NullType, Null, DataObject, OrderedDict, generator_types, from_data_gen)"},
    {NULL, NULL, 0, NULL},
};


static struct PyModuleDef speedups_module = {
    PyModuleDef_HEAD_INIT, "_speedups", "C accelerators for mo_dots", -1, speedups_methods,
};


PyMODINIT_FUNC
PyInit__speedups(void)
{
    PyObject *m;

    slot_str = PyUnicode_InternFromString("_internal_value");
    empty_str = PyUnicode_InternFromString("");
    null_repr_str = PyUnicode_InternFromString("Null");
    dot_str = PyUnicode_InternFromString(".");
    json_str = PyUnicode_InternFromString("__json__");
    call_str = PyUnicode_InternFromString("__call__");
    list_contains_meth = PyObject_GetAttrString((PyObject *)&PyList_Type, "__contains__");
    empty_tuple = PyTuple_New(0);
    null_types_tuple = PyTuple_New(0);
    missing_types_tuple = PyTuple_New(0);
    sequence_types_tuple = PyTuple_New(0);
    data_types_tuple = PyTuple_New(0);
    many_types_tuple = PyTuple_New(0);
    if (!slot_str || !empty_str || !null_repr_str || !dot_str || !json_str || !call_str
        || !list_contains_meth || !empty_tuple || !null_types_tuple || !missing_types_tuple
        || !sequence_types_tuple || !data_types_tuple || !many_types_tuple)
        return NULL;
    null_hash = PyObject_Hash(Py_None);

    if (PyType_Ready(&StoreBase_Type) < 0)
        return NULL;
    if (PyType_Ready(&DataBase_Type) < 0)
        return NULL;
    if (PyType_Ready(&NullBase_Type) < 0)
        return NULL;
    if (PyType_Ready(&ListBase_Type) < 0)
        return NULL;

    m = PyModule_Create(&speedups_module);
    if (m == NULL)
        return NULL;
    Py_INCREF(&StoreBase_Type);
    if (PyModule_AddObject(m, "_StoreBase", (PyObject *)&StoreBase_Type) < 0)
        return NULL;
    Py_INCREF(&DataBase_Type);
    if (PyModule_AddObject(m, "_DataBase", (PyObject *)&DataBase_Type) < 0)
        return NULL;
    Py_INCREF(&NullBase_Type);
    if (PyModule_AddObject(m, "_NullBase", (PyObject *)&NullBase_Type) < 0)
        return NULL;
    Py_INCREF(&ListBase_Type);
    if (PyModule_AddObject(m, "_ListBase", (PyObject *)&ListBase_Type) < 0)
        return NULL;
    return m;
}
