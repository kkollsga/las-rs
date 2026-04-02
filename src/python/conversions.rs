use numpy::PyArray1;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyFloat, PyInt};

use crate::core::errors::LasError;
use crate::core::types::{CurveItem, HeaderItem, ItemWrapper, Value};

// ---------------------------------------------------------------------------
// Value conversions
// ---------------------------------------------------------------------------

impl Value {
    pub fn to_py(&self, py: Python<'_>) -> PyObject {
        match self {
            Value::Str(s) => s.into_pyobject(py).unwrap().into_any().unbind(),
            Value::Int(i) => i.into_pyobject(py).unwrap().into_any().unbind(),
            Value::Float(f) => f.into_pyobject(py).unwrap().into_any().unbind(),
        }
    }

    pub fn from_py(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
        // Handle None -> empty string
        if obj.is_none() {
            return Ok(Value::Str(String::new()));
        }
        // Check bool before int since bool is a subclass of int in Python
        if obj.is_instance_of::<PyBool>() {
            let b: bool = obj.extract()?;
            return Ok(Value::Int(if b { 1 } else { 0 }));
        }
        if obj.is_instance_of::<PyInt>() {
            let i: i64 = obj.extract()?;
            return Ok(Value::Int(i));
        }
        if obj.is_instance_of::<PyFloat>() {
            let f: f64 = obj.extract()?;
            return Ok(Value::Float(f));
        }
        let s: String = obj.extract()?;
        Ok(Value::Str(s))
    }
}

// ---------------------------------------------------------------------------
// ItemWrapper conversions
// ---------------------------------------------------------------------------

impl ItemWrapper {
    pub fn to_py(&self, py: Python<'_>) -> PyObject {
        match self {
            ItemWrapper::Header(h) => {
                Py::new(py, h.clone()).unwrap().into_any()
            }
            ItemWrapper::Curve(c) => {
                Py::new(py, c.clone()).unwrap().into_any()
            }
        }
    }

    pub fn from_py(obj: &Bound<'_, PyAny>) -> PyResult<ItemWrapper> {
        if let Ok(c) = obj.extract::<CurveItem>() {
            Ok(ItemWrapper::Curve(c))
        } else if let Ok(h) = obj.extract::<HeaderItem>() {
            Ok(ItemWrapper::Header(h))
        } else {
            Err(pyo3::exceptions::PyTypeError::new_err("Expected HeaderItem or CurveItem"))
        }
    }
}

// ---------------------------------------------------------------------------
// LasError -> PyErr conversion
// ---------------------------------------------------------------------------

impl From<LasError> for PyErr {
    fn from(err: LasError) -> PyErr {
        match err {
            LasError::Header(msg) => crate::python::errors::LASHeaderError::new_err(msg),
            LasError::Data(msg) => crate::python::errors::LASDataError::new_err(msg),
            LasError::UnknownUnit(msg) => crate::python::errors::LASUnknownUnitError::new_err(msg),
            LasError::Io(msg) => pyo3::exceptions::PyIOError::new_err(msg),
            LasError::KeyError(msg) => pyo3::exceptions::PyKeyError::new_err(msg),
        }
    }
}

// ---------------------------------------------------------------------------
// Kwargs helpers
// ---------------------------------------------------------------------------

pub fn kwarg_string<'a>(kwargs: Option<&'a Bound<'_, pyo3::types::PyDict>>, key: &str, default: &str) -> String {
    kwargs
        .and_then(|kw| kw.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<String>().ok())
        .unwrap_or_else(|| default.to_string())
}

pub fn kwarg_f64(kwargs: Option<&Bound<'_, pyo3::types::PyDict>>, key: &str) -> Option<f64> {
    kwargs
        .and_then(|kw| kw.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<f64>().ok())
}

pub fn kwarg_bool(kwargs: Option<&Bound<'_, pyo3::types::PyDict>>, key: &str, default: bool) -> bool {
    kwargs
        .and_then(|kw| kw.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<bool>().ok())
        .unwrap_or(default)
}

pub fn kwarg_opt_string(kwargs: Option<&Bound<'_, pyo3::types::PyDict>>, key: &str) -> Option<String> {
    kwargs
        .and_then(|kw| kw.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<String>().ok())
}

// ---------------------------------------------------------------------------
// extract_curve_data
// ---------------------------------------------------------------------------

pub fn extract_curve_data(data: Option<&Bound<'_, PyAny>>) -> PyResult<Vec<f64>> {
    match data {
        Some(d) => {
            if let Ok(arr) = d.extract::<Vec<f64>>() {
                Ok(arr)
            } else if let Ok(arr_ref) = d.downcast::<PyArray1<f64>>() {
                use numpy::PyArrayMethods;
                arr_ref.to_vec().map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("{}", e)))
            } else {
                Ok(Vec::new())
            }
        }
        None => Ok(Vec::new()),
    }
}
