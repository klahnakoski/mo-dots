/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
 *
 * Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
 *
 * C ACCELERATORS FOR mo_dots HOT FUNCTIONS
 *
 * Pure-Python equivalents remain in utils.py / __init__.py; this module is
 * optional and the package falls back when it is absent.  Semantics must
 * match the Python versions exactly - the test suite is the conformance test.
 *
 * Wiring: utils.py calls _sync() at import and on every type registration;
 * mo_dots/__init__.py calls _init() once all classes exist, then rebinds the
 * module-level names before export() distributes them.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>

static PyObject *DataClass = NULL;       /* mo_dots.datas.Data           */
static PyObject *FlatListClass = NULL;   /* mo_dots.lists.FlatList       */
static PyObject *NullTypeClass = NULL;   /* mo_dots.nones.NullType       */
static PyObject *NullSingleton = NULL;   /* mo_dots.nones.Null           */
static PyObject *DataObjectClass = NULL; /* mo_dots.objects.DataObject   */
static PyObject *OrderedDictClass = NULL;
static PyObject *generator_types = NULL; /* tuple of generator classes   */
static PyObject *from_data_gen = NULL;   /* lazy generator helper        */
static PyObject *slot_str = NULL;        /* "_internal_value"            */

static PyObject *null_types_tuple = NULL;    /* tuple of null classes    */
static PyObject *missing_types_tuple = NULL; /* (str, *null, *many)      */

/* slot descriptors, cached so wrap/unwrap skips the MRO walk */
static PyObject *data_slot_descr = NULL;
static PyObject *flat_slot_descr = NULL;


static inline int
type_in_tuple(PyTypeObject *t, PyObject *tuple)
{
    Py_ssize_t i, n = PyTuple_GET_SIZE(tuple);
    for (i = 0; i < n; i++) {
        if (PyTuple_GET_ITEM(tuple, i) == (PyObject *)t)
            return 1;
    }
    return 0;
}


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


/* EQUIVALENT OF _new(cls) PLUS _set(m, SLOT, value): NO __init__, NO __setattr__ */
static PyObject *
new_wrapped(PyObject *cls, PyObject *slot_descr, PyObject *value)
{
    PyTypeObject *tp = (PyTypeObject *)cls;
    PyObject *m = tp->tp_alloc(tp, 0);
    if (m == NULL)
        return NULL;
    if (Py_TYPE(slot_descr)->tp_descr_set(slot_descr, m, value) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    return m;
}


static PyObject *
speedups_dict_to_data(PyObject *self, PyObject *d)
{
    return new_wrapped(DataClass, data_slot_descr, d);
}


static PyObject *
speedups_list_to_data(PyObject *self, PyObject *v)
{
    return new_wrapped(FlatListClass, flat_slot_descr, v);
}


static PyObject *speedups_from_data(PyObject *self, PyObject *v);


static PyObject *
c_to_data(PyObject *v)
{
    PyTypeObject *t = Py_TYPE(v);

    if (t == &PyDict_Type || (PyObject *)t == OrderedDictClass)
        return new_wrapped(DataClass, data_slot_descr, v);
    if (v == Py_None) {
        Py_INCREF(NullSingleton);
        return NullSingleton;
    }
    if (t == &PyList_Type || t == &PyTuple_Type)
        return new_wrapped(FlatListClass, flat_slot_descr, v);
    if (type_in_tuple(t, generator_types)) {
        /* list_to_data(list(from_data(vv) for vv in v)) */
        PyObject *item, *converted, *out;
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
        PyObject *result = new_wrapped(FlatListClass, flat_slot_descr, out);
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
    if (v == Py_None)
        Py_RETURN_NONE;

    PyObject *t = (PyObject *)Py_TYPE(v);
    if (t == NullTypeClass)
        Py_RETURN_NONE;
    if (t == DataClass)
        return Py_TYPE(data_slot_descr)->tp_descr_get(data_slot_descr, v, DataClass);
    if (t == FlatListClass)
        return Py_TYPE(flat_slot_descr)->tp_descr_get(flat_slot_descr, v, FlatListClass);
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
speedups_sync(PyObject *self, PyObject *args)
{
    PyObject *nulls, *missings;
    if (!PyArg_ParseTuple(args, "O!O!", &PyTuple_Type, &nulls, &PyTuple_Type, &missings))
        return NULL;
    Py_INCREF(nulls);
    Py_XSETREF(null_types_tuple, nulls);
    Py_INCREF(missings);
    Py_XSETREF(missing_types_tuple, missings);
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

    PyObject *d_descr = PyObject_GetAttr(data, slot_str);
    if (d_descr == NULL)
        return NULL;
    PyObject *f_descr = PyObject_GetAttr(flat, slot_str);
    if (f_descr == NULL) {
        Py_DECREF(d_descr);
        return NULL;
    }
    if (Py_TYPE(d_descr)->tp_descr_set == NULL || Py_TYPE(f_descr)->tp_descr_set == NULL) {
        Py_DECREF(d_descr);
        Py_DECREF(f_descr);
        PyErr_SetString(PyExc_TypeError, "expected slot descriptors on Data and FlatList");
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
    Py_XSETREF(data_slot_descr, d_descr);
    Py_XSETREF(flat_slot_descr, f_descr);
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
    {"_sync", speedups_sync, METH_VARARGS, "(null_types, missing_types) - refresh type registries"},
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
    slot_str = PyUnicode_InternFromString("_internal_value");
    if (slot_str == NULL)
        return NULL;
    /* EMPTY REGISTRIES UNTIL _sync(); is_null ON AN UNSYNCED MODULE ANSWERS False */
    null_types_tuple = PyTuple_New(0);
    missing_types_tuple = PyTuple_New(0);
    if (null_types_tuple == NULL || missing_types_tuple == NULL)
        return NULL;
    return PyModule_Create(&speedups_module);
}
