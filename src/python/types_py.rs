use numpy::{PyArray1, PyArrayMethods};
use pyo3::exceptions::{PyKeyError, PyIndexError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PySlice, PyTuple};

use crate::core::types::{CurveItem, HeaderItem, ItemWrapper, SectionItems, Value};

// ---------------------------------------------------------------------------
// HeaderItem
// ---------------------------------------------------------------------------

#[pymethods]
impl HeaderItem {
    #[new]
    #[pyo3(signature = (mnemonic="", unit="", value=None, descr="", data=None))]
    fn py_new(
        mnemonic: &str,
        unit: &str,
        value: Option<&Bound<'_, PyAny>>,
        descr: &str,
        data: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let val = match value {
            Some(v) => Value::from_py(v)?,
            None => Value::Str(String::new()),
        };
        let dat = match data {
            Some(d) => Value::from_py(d)?,
            None => Value::Str(String::new()),
        };
        Ok(HeaderItem {
            original_mnemonic: mnemonic.to_string(),
            session_mnemonic: mnemonic.to_string(),
            unit: unit.to_string(),
            value: val,
            descr: descr.to_string(),
            data: dat,
        })
    }

    #[getter]
    fn mnemonic(&self) -> &str {
        &self.session_mnemonic
    }

    #[setter]
    fn set_mnemonic(&mut self, name: &str) {
        self.original_mnemonic = name.to_string();
        self.session_mnemonic = name.to_string();
    }

    #[getter]
    fn get_original_mnemonic(&self) -> &str {
        &self.original_mnemonic
    }

    #[getter]
    fn useful_mnemonic(&self) -> &str {
        if self.original_mnemonic.is_empty() {
            "UNKNOWN"
        } else {
            &self.original_mnemonic
        }
    }

    #[setter]
    fn set_useful_mnemonic(&self, _val: &str) -> PyResult<()> {
        Err(PyValueError::new_err("useful_mnemonic is read-only"))
    }

    #[getter]
    fn get_unit(&self) -> &str {
        &self.unit
    }

    #[setter]
    fn set_unit(&mut self, unit: &str) {
        self.unit = unit.to_string();
    }

    #[getter]
    fn get_value(&self, py: Python<'_>) -> PyObject {
        self.value.to_py(py)
    }

    #[setter]
    fn set_value(&mut self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.value = Value::from_py(value)?;
        Ok(())
    }

    #[getter]
    fn get_descr(&self) -> &str {
        &self.descr
    }

    #[setter]
    fn set_descr(&mut self, descr: &str) {
        self.descr = descr.to_string();
    }

    #[getter]
    fn get_data(&self, py: Python<'_>) -> PyObject {
        self.data.to_py(py)
    }

    #[setter]
    fn set_data(&mut self, data: &Bound<'_, PyAny>) -> PyResult<()> {
        self.data = Value::from_py(data)?;
        Ok(())
    }

    /// Internal method used by SectionItems to set session mnemonic without touching original
    fn set_session_mnemonic_only(&mut self, name: String) {
        self.session_mnemonic = name;
    }

    fn __getitem__(&self, py: Python<'_>, key: &str) -> PyResult<PyObject> {
        match key {
            "mnemonic" => Ok(self.session_mnemonic.clone().into_pyobject(py).unwrap().into_any().unbind()),
            "unit" => Ok(self.unit.clone().into_pyobject(py).unwrap().into_any().unbind()),
            "value" => Ok(self.value.to_py(py)),
            "descr" => Ok(self.descr.clone().into_pyobject(py).unwrap().into_any().unbind()),
            "original_mnemonic" => Ok(self.original_mnemonic.clone().into_pyobject(py).unwrap().into_any().unbind()),
            "useful_mnemonic" => {
                let um = if self.original_mnemonic.is_empty() { "UNKNOWN" } else { &self.original_mnemonic };
                Ok(um.into_pyobject(py).unwrap().into_any().unbind())
            },
            "data" => Ok(self.data.to_py(py)),
            _ => Err(PyKeyError::new_err(key.to_string())),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "HeaderItem(mnemonic=\"{}\", unit=\"{}\", value={}, descr=\"{}\")",
            self.session_mnemonic,
            self.unit,
            self.value,
            self.descr,
        )
    }

    fn __getnewargs_ex__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let args = PyTuple::empty(py);
        let kwargs = PyDict::new(py);
        kwargs.set_item("mnemonic", &self.original_mnemonic)?;
        kwargs.set_item("unit", &self.unit)?;
        kwargs.set_item("value", self.value.to_py(py))?;
        kwargs.set_item("descr", &self.descr)?;
        PyTuple::new(py, &[args.into_any(), kwargs.into_any()])
    }

    fn __eq__(&self, _py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<bool> {
        if let Ok(o) = other.extract::<HeaderItem>() {
            Ok(self.original_mnemonic == o.original_mnemonic
                && self.unit == o.unit
                && self.descr == o.descr
                && self.value.display_str() == o.value.display_str())
        } else {
            Ok(false)
        }
    }

    #[getter]
    fn json(&self) -> PyResult<String> {
        let mut map = serde_json::Map::new();
        map.insert("mnemonic".to_string(), serde_json::Value::String(self.original_mnemonic.clone()));
        map.insert("unit".to_string(), serde_json::Value::String(self.unit.clone()));
        map.insert("value".to_string(), self.value.to_json_value());
        map.insert("descr".to_string(), serde_json::Value::String(self.descr.clone()));
        Ok(serde_json::to_string(&serde_json::Value::Object(map)).unwrap())
    }

    #[setter]
    fn set_json(&self, _val: &str) -> PyResult<()> {
        Err(pyo3::exceptions::PyException::new_err("Cannot set json property directly"))
    }
}

// ---------------------------------------------------------------------------
// CurveItem
// ---------------------------------------------------------------------------

#[pymethods]
impl CurveItem {
    #[new]
    #[pyo3(signature = (mnemonic="", unit="", value=None, descr="", data=None))]
    fn py_new(
        py: Python<'_>,
        mnemonic: &str,
        unit: &str,
        value: Option<&Bound<'_, PyAny>>,
        descr: &str,
        data: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let val = match value {
            Some(v) => Value::from_py(v)?,
            None => Value::Str(String::new()),
        };
        let curve_data = match data {
            Some(d) => {
                // Try to extract as numpy array or list of f64
                if let Ok(arr) = d.extract::<Vec<f64>>() {
                    arr
                } else if let Ok(arr_ref) = d.downcast::<PyArray1<f64>>() {
                    arr_ref.to_vec()?
                } else {
                    Vec::new()
                }
            }
            None => Vec::new(),
        };

        Ok(CurveItem {
            header: HeaderItem {
                original_mnemonic: mnemonic.to_string(),
                session_mnemonic: mnemonic.to_string(),
                unit: unit.to_string(),
                value: val,
                descr: descr.to_string(),
                data: Value::Str(String::new()),
            },
            curve_data,
            string_data: None,
            dtype_override: None,
        })
    }

    #[getter]
    fn mnemonic(&self) -> &str {
        &self.header.session_mnemonic
    }

    #[setter]
    fn set_mnemonic(&mut self, name: &str) {
        self.header.original_mnemonic = name.to_string();
        self.header.session_mnemonic = name.to_string();
    }

    #[getter]
    fn original_mnemonic(&self) -> &str {
        &self.header.original_mnemonic
    }

    #[getter]
    fn useful_mnemonic(&self) -> &str {
        if self.header.original_mnemonic.is_empty() {
            "UNKNOWN"
        } else {
            &self.header.original_mnemonic
        }
    }

    #[getter]
    fn get_unit(&self) -> &str {
        &self.header.unit
    }

    #[setter]
    fn set_unit(&mut self, unit: &str) {
        self.header.unit = unit.to_string();
    }

    #[getter]
    fn get_value(&self, py: Python<'_>) -> PyObject {
        self.header.value.to_py(py)
    }

    #[setter]
    fn set_value(&mut self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.header.value = Value::from_py(value)?;
        Ok(())
    }

    #[getter]
    fn get_descr(&self) -> &str {
        &self.header.descr
    }

    #[setter]
    fn set_descr(&mut self, descr: &str) {
        self.header.descr = descr.to_string();
    }

    #[getter]
    fn API_code(&self, py: Python<'_>) -> PyObject {
        self.header.value.to_py(py)
    }

    #[setter]
    fn set_API_code(&mut self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.header.value = Value::from_py(value)?;
        Ok(())
    }

    #[getter]
    fn data<'py>(&self, py: Python<'py>) -> PyResult<PyObject> {
        // Return string data if available
        if let Some(ref strings) = self.string_data {
            let np = py.import("numpy")?;
            let list = PyList::new(py, strings.iter().map(|s| s.as_str()))?;
            let kwargs = PyDict::new(py);
            let builtins = py.import("builtins")?;
            kwargs.set_item("dtype", builtins.getattr("object")?)?;
            let arr = np.call_method("array", (list,), Some(&kwargs))?;
            return Ok(arr.unbind());
        }
        // Check for dtype override
        if let Some(ref dtype) = self.dtype_override {
            if dtype == "int" {
                let int_data: Vec<i64> = self.curve_data.iter()
                    .map(|v| if v.is_nan() { 0i64 } else { *v as i64 })
                    .collect();
                let arr = numpy::PyArray1::from_vec(py, int_data);
                return Ok(arr.into_any().unbind());
            }
        }
        Ok(PyArray1::from_vec(py, self.curve_data.clone()).into_any().unbind())
    }

    #[setter]
    fn set_data(&mut self, data: &Bound<'_, PyAny>) -> PyResult<()> {
        if let Ok(arr) = data.extract::<Vec<f64>>() {
            self.curve_data = arr;
            self.string_data = None;
        } else if let Ok(arr_ref) = data.downcast::<PyArray1<f64>>() {
            self.curve_data = arr_ref.to_vec().map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("{}", e)))?;
            self.string_data = None;
        } else if let Ok(strings) = data.extract::<Vec<String>>() {
            self.string_data = Some(strings);
        } else {
            return Err(PyTypeError::new_err("data must be array-like of floats or list of strings"));
        }
        Ok(())
    }

    fn set_session_mnemonic_only(&mut self, name: String) {
        self.header.session_mnemonic = name;
    }

    fn __getnewargs_ex__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let args = PyTuple::empty(py);
        let kwargs = PyDict::new(py);
        kwargs.set_item("mnemonic", &self.header.original_mnemonic)?;
        kwargs.set_item("unit", &self.header.unit)?;
        kwargs.set_item("value", self.header.value.to_py(py))?;
        kwargs.set_item("descr", &self.header.descr)?;
        // data as list for pickle
        let data_list = pyo3::types::PyList::new(py, self.curve_data.iter().copied())?;
        kwargs.set_item("data", data_list)?;
        PyTuple::new(py, &[args.into_any(), kwargs.into_any()])
    }

    fn __getitem__(&self, py: Python<'_>, key: &str) -> PyResult<PyObject> {
        match key {
            "mnemonic" => Ok(self.header.session_mnemonic.clone().into_pyobject(py).unwrap().into_any().unbind()),
            "unit" => Ok(self.header.unit.clone().into_pyobject(py).unwrap().into_any().unbind()),
            "value" => Ok(self.header.value.to_py(py)),
            "descr" => Ok(self.header.descr.clone().into_pyobject(py).unwrap().into_any().unbind()),
            "original_mnemonic" => Ok(self.header.original_mnemonic.clone().into_pyobject(py).unwrap().into_any().unbind()),
            "useful_mnemonic" => {
                let um = if self.header.original_mnemonic.is_empty() { "UNKNOWN" } else { &self.header.original_mnemonic };
                Ok(um.into_pyobject(py).unwrap().into_any().unbind())
            },
            "data" => self.data(py),
            _ => Err(PyKeyError::new_err(key.to_string())),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "CurveItem(mnemonic=\"{}\", unit=\"{}\", value={}, descr=\"{}\", data.shape=({},))",
            self.header.session_mnemonic,
            self.header.unit,
            self.header.value,
            self.header.descr,
            self.curve_data.len(),
        )
    }

    #[getter]
    fn json(&self) -> PyResult<String> {
        let mut map = serde_json::Map::new();
        map.insert("mnemonic".to_string(), serde_json::Value::String(self.header.original_mnemonic.clone()));
        map.insert("unit".to_string(), serde_json::Value::String(self.header.unit.clone()));
        map.insert("value".to_string(), self.header.value.to_json_value());
        map.insert("descr".to_string(), serde_json::Value::String(self.header.descr.clone()));
        let data_vals: Vec<serde_json::Value> = self.curve_data.iter().map(|v| {
            if v.is_nan() {
                serde_json::Value::Null
            } else {
                serde_json::json!(*v)
            }
        }).collect();
        map.insert("data".to_string(), serde_json::Value::Array(data_vals));
        Ok(serde_json::to_string(&serde_json::Value::Object(map)).unwrap())
    }

    #[setter]
    fn set_json(&self, _val: &str) -> PyResult<()> {
        Err(pyo3::exceptions::PyException::new_err("Cannot set json property directly"))
    }
}

// ---------------------------------------------------------------------------
// SectionItems
// ---------------------------------------------------------------------------

#[pymethods]
impl SectionItems {
    #[new]
    #[pyo3(signature = (items_or_transforms=None, mnemonic_transforms=true))]
    fn py_new(
        items_or_transforms: Option<&Bound<'_, PyAny>>,
        mnemonic_transforms: bool,
    ) -> PyResult<Self> {
        let mut section = SectionItems {
            items: Vec::new(),
            mnemonic_transforms,
        };

        // If first arg is a list of items, populate the section
        if let Some(arg) = items_or_transforms {
            // Check if it's a bool (legacy mnemonic_transforms positional arg)
            if let Ok(b) = arg.extract::<bool>() {
                section.mnemonic_transforms = b;
            } else if let Ok(list) = arg.extract::<Vec<Bound<'_, PyAny>>>() {
                for item_obj in &list {
                    let wrapper = ItemWrapper::from_py(item_obj)?;
                    section.items.push(wrapper);
                }
                section.assign_duplicate_suffixes_all();
            }
        }

        Ok(section)
    }

    fn __len__(&self) -> usize {
        self.items.len()
    }

    #[getter]
    fn get_mnemonic_transforms(&self) -> bool {
        self.mnemonic_transforms
    }

    #[setter]
    fn set_mnemonic_transforms(&mut self, val: bool) {
        self.mnemonic_transforms = val;
    }

    #[pyo3(signature = (test_mnemonic=None))]
    fn assign_duplicate_suffixes(&mut self, test_mnemonic: Option<&str>) {
        match test_mnemonic {
            Some(m) => self.assign_duplicate_suffixes_for(m),
            None => self.assign_duplicate_suffixes_all(),
        }
    }

    fn __getitem__(&self, py: Python<'_>, key: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        // Try integer index
        if let Ok(idx) = key.extract::<isize>() {
            let len = self.items.len() as isize;
            let actual = if idx < 0 { len + idx } else { idx };
            if actual < 0 || actual >= len {
                return Err(PyIndexError::new_err("index out of range"));
            }
            return Ok(self.items[actual as usize].to_py(py));
        }

        // Try slice
        if let Ok(slice) = key.downcast::<PySlice>() {
            let len = self.items.len();
            let indices = slice.indices(len as isize)?;
            let mut new_items = Vec::new();
            let mut i = indices.start;
            while (indices.step > 0 && i < indices.stop) || (indices.step < 0 && i > indices.stop) {
                if i >= 0 && (i as usize) < len {
                    new_items.push(self.items[i as usize].clone());
                }
                i += indices.step;
            }
            let sec = SectionItems {
                items: new_items,
                mnemonic_transforms: self.mnemonic_transforms,
            };
            return Ok(Py::new(py, sec)?.into_any());
        }

        // Try string mnemonic
        if let Ok(mnemonic) = key.extract::<String>() {
            if let Some(idx) = self.find_index_by_mnemonic(&mnemonic) {
                return Ok(self.items[idx].to_py(py));
            }
            return Err(PyKeyError::new_err(mnemonic));
        }

        Err(PyTypeError::new_err("indices must be integers, slices, or mnemonic strings"))
    }

    fn __setitem__(&mut self, _py: Python<'_>, key: &Bound<'_, PyAny>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        // Try integer index
        if let Ok(idx) = key.extract::<isize>() {
            let len = self.items.len() as isize;
            let actual = if idx < 0 { len + idx } else { idx };
            if actual < 0 || actual >= len {
                return Err(PyIndexError::new_err("index out of range"));
            }
            let wrapper = ItemWrapper::from_py(value)?;
            self.items[actual as usize] = wrapper;
            return Ok(());
        }

        // Try string mnemonic
        if let Ok(mnemonic) = key.extract::<String>() {
            if let Some(idx) = self.find_index_by_mnemonic(&mnemonic) {
                // If value is a HeaderItem/CurveItem, replace the whole item
                if let Ok(wrapper) = ItemWrapper::from_py(value) {
                    self.items[idx] = wrapper;
                } else {
                    // Otherwise treat as setting the .value field
                    let val = Value::from_py(value)?;
                    self.items[idx].set_value(val);
                }
                return Ok(());
            }
            return Err(PyKeyError::new_err(mnemonic));
        }

        Err(PyTypeError::new_err("key must be integer or mnemonic string"))
    }

    fn __delitem__(&mut self, key: &Bound<'_, PyAny>) -> PyResult<()> {
        // Try integer index
        if let Ok(idx) = key.extract::<isize>() {
            let len = self.items.len() as isize;
            let actual = if idx < 0 { len + idx } else { idx };
            if actual < 0 || actual >= len {
                return Err(PyIndexError::new_err("index out of range"));
            }
            self.items.remove(actual as usize);
            return Ok(());
        }

        // Try string mnemonic
        if let Ok(mnemonic) = key.extract::<String>() {
            if let Some(idx) = self.find_index_by_mnemonic(&mnemonic) {
                self.items.remove(idx);
                return Ok(());
            }
            return Err(PyKeyError::new_err(mnemonic));
        }

        Err(PyTypeError::new_err("key must be integer or mnemonic string"))
    }

    fn __contains__(&self, key: &Bound<'_, PyAny>) -> PyResult<bool> {
        // Check if it's a string mnemonic
        if let Ok(mnemonic) = key.extract::<String>() {
            return Ok(self.find_index_by_mnemonic(&mnemonic).is_some());
        }

        // Check if it's a HeaderItem or CurveItem by comparing mnemonics
        if let Ok(h) = key.extract::<HeaderItem>() {
            return Ok(self.find_index_by_mnemonic(&h.session_mnemonic).is_some());
        }
        if let Ok(c) = key.extract::<CurveItem>() {
            return Ok(self.find_index_by_mnemonic(&c.header.session_mnemonic).is_some());
        }

        Ok(false)
    }

    fn __iter__(&self, py: Python<'_>) -> PyResult<PyObject> {
        let list = PyList::new(py, self.items.iter().map(|item| item.to_py(py)))?;
        Ok(list.call_method0("__iter__")?.unbind())
    }

    fn append(&mut self, item: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut wrapper = ItemWrapper::from_py(item)?;
        // Auto-rename empty mnemonics to "UNKNOWN"
        if wrapper.original_mnemonic().is_empty() {
            match &mut wrapper {
                ItemWrapper::Header(h) => {
                    h.original_mnemonic = "UNKNOWN".to_string();
                    h.session_mnemonic = "UNKNOWN".to_string();
                }
                ItemWrapper::Curve(c) => {
                    c.header.original_mnemonic = "UNKNOWN".to_string();
                    c.header.session_mnemonic = "UNKNOWN".to_string();
                }
            }
        }
        let mnemonic = wrapper.original_mnemonic().to_string();
        self.items.push(wrapper);
        self.assign_duplicate_suffixes_for(&mnemonic);
        Ok(())
    }

    fn insert(&mut self, index: usize, item: &Bound<'_, PyAny>) -> PyResult<()> {
        let wrapper = ItemWrapper::from_py(item)?;
        let mnemonic = wrapper.original_mnemonic().to_string();
        let idx = index.min(self.items.len());
        self.items.insert(idx, wrapper);
        self.assign_duplicate_suffixes_for(&mnemonic);
        Ok(())
    }

    fn keys(&self) -> Vec<String> {
        self.items.iter().map(|item| item.session_mnemonic().to_string()).collect()
    }

    fn values(&self, py: Python<'_>) -> PyResult<Vec<PyObject>> {
        Ok(self.items.iter().map(|item| item.to_py(py)).collect())
    }

    fn items(&self, py: Python<'_>) -> PyResult<Vec<(String, PyObject)>> {
        Ok(self.items.iter().map(|item| {
            (item.session_mnemonic().to_string(), item.to_py(py))
        }).collect())
    }

    fn iterkeys(&self) -> Vec<String> {
        self.keys()
    }

    fn itervalues(&self, py: Python<'_>) -> PyResult<Vec<PyObject>> {
        self.values(py)
    }

    fn iteritems(&self, py: Python<'_>) -> PyResult<Vec<(String, PyObject)>> {
        self.items(py)
    }

    #[pyo3(signature = (mnemonic, default=None, add=false))]
    fn get(&mut self, py: Python<'_>, mnemonic: &str, default: Option<&Bound<'_, PyAny>>, add: bool) -> PyResult<PyObject> {
        if let Some(idx) = self.find_index_by_mnemonic(mnemonic) {
            return Ok(self.items[idx].to_py(py));
        }

        // Check if default is a HeaderItem or CurveItem object
        if let Some(d) = default {
            if let Ok(h) = d.extract::<HeaderItem>() {
                let new_item = HeaderItem {
                    original_mnemonic: mnemonic.to_string(),
                    session_mnemonic: mnemonic.to_string(),
                    unit: h.unit.clone(),
                    value: h.value.clone(),
                    descr: h.descr.clone(),
                    data: h.data.clone(),
                };
                if add {
                    let wrapper = ItemWrapper::Header(new_item.clone());
                    self.items.push(wrapper);
                    self.assign_duplicate_suffixes_for(mnemonic);
                }
                return Ok(Py::new(py, new_item)?.into_any());
            }
            if let Ok(c) = d.extract::<CurveItem>() {
                let new_item = CurveItem {
                    header: HeaderItem {
                        original_mnemonic: mnemonic.to_string(),
                        session_mnemonic: mnemonic.to_string(),
                        unit: c.header.unit.clone(),
                        value: c.header.value.clone(),
                        descr: c.header.descr.clone(),
                        data: c.header.data.clone(),
                    },
                    curve_data: c.curve_data.clone(),
                    string_data: None,
                    dtype_override: None,
                };
                if add {
                    let wrapper = ItemWrapper::Curve(new_item.clone());
                    self.items.push(wrapper);
                    self.assign_duplicate_suffixes_for(mnemonic);
                }
                return Ok(Py::new(py, new_item)?.into_any());
            }
        }

        // Check if section contains CurveItems -- if so, return a CurveItem with NaN data
        let has_curves = self.items.iter().any(|item| matches!(item, ItemWrapper::Curve(_)));
        if has_curves {
            // Find the data length from existing curves
            let data_len = self.items.iter().find_map(|item| {
                if let ItemWrapper::Curve(c) = item {
                    if !c.curve_data.is_empty() {
                        Some(c.curve_data.len())
                    } else {
                        None
                    }
                } else {
                    None
                }
            }).unwrap_or(0);

            let val = match default {
                Some(d) => Value::from_py(d)?,
                None => Value::Str(String::new()),
            };

            let new_item = CurveItem {
                header: HeaderItem {
                    original_mnemonic: mnemonic.to_string(),
                    session_mnemonic: mnemonic.to_string(),
                    unit: String::new(),
                    value: val,
                    descr: String::new(),
                    data: Value::Str(String::new()),
                },
                curve_data: vec![f64::NAN; data_len],
                string_data: None,
                dtype_override: None,
            };
            if add {
                let wrapper = ItemWrapper::Curve(new_item.clone());
                self.items.push(wrapper);
                self.assign_duplicate_suffixes_for(mnemonic);
            }
            return Ok(Py::new(py, new_item)?.into_any());
        }

        // Default: create a HeaderItem
        let val = match default {
            Some(d) => Value::from_py(d)?,
            None => Value::Str(String::new()),
        };

        let new_item = HeaderItem {
            original_mnemonic: mnemonic.to_string(),
            session_mnemonic: mnemonic.to_string(),
            unit: String::new(),
            value: val,
            descr: String::new(),
            data: Value::Str(String::new()),
        };

        if add {
            let wrapper = ItemWrapper::Header(new_item.clone());
            self.items.push(wrapper);
            self.assign_duplicate_suffixes_for(mnemonic);
        }

        Ok(Py::new(py, new_item)?.into_any())
    }

    fn dictview(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        for item in &self.items {
            dict.set_item(item.session_mnemonic(), item.value().to_py(py))?;
        }
        Ok(dict.into_any().unbind())
    }

    fn set_item(&mut self, mnemonic: &str, item: &Bound<'_, PyAny>) -> PyResult<()> {
        let wrapper = ItemWrapper::from_py(item)?;
        if let Some(idx) = self.find_index_by_mnemonic(mnemonic) {
            self.items[idx] = wrapper;
        } else {
            self.items.push(wrapper);
        }
        Ok(())
    }

    fn set_item_value(&mut self, mnemonic: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
        if let Some(idx) = self.find_index_by_mnemonic(mnemonic) {
            let val = Value::from_py(value)?;
            self.items[idx].set_value(val);
            Ok(())
        } else {
            Err(PyKeyError::new_err(mnemonic.to_string()))
        }
    }

    fn __getattr__(&self, py: Python<'_>, name: &str) -> PyResult<PyObject> {
        if let Some(idx) = self.find_index_by_mnemonic(name) {
            return Ok(self.items[idx].to_py(py));
        }
        Err(pyo3::exceptions::PyAttributeError::new_err(format!("'SectionItems' has no attribute '{}'", name)))
    }

    fn __setattr__(&mut self, _py: Python<'_>, name: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
        // Check for known Python-level attributes first
        if name == "mnemonic_transforms" {
            self.mnemonic_transforms = value.extract()?;
            return Ok(());
        }

        if let Some(idx) = self.find_index_by_mnemonic(name) {
            // If value is a HeaderItem/CurveItem, replace
            if let Ok(wrapper) = ItemWrapper::from_py(value) {
                self.items[idx] = wrapper;
            } else {
                let val = Value::from_py(value)?;
                self.items[idx].set_value(val);
            }
            return Ok(());
        }

        Err(pyo3::exceptions::PyAttributeError::new_err(format!("'SectionItems' has no attribute '{}'", name)))
    }

    fn __str__(&self) -> String {
        if self.items.is_empty() {
            return String::new();
        }

        // Calculate column widths
        let mut mnem_w = 0usize;
        let mut unit_w = 0usize;
        let mut val_w = 0usize;

        for item in &self.items {
            mnem_w = mnem_w.max(item.session_mnemonic().len());
            unit_w = unit_w.max(item.unit().len());
            val_w = val_w.max(item.value().display_str().len());
        }

        let mut lines = Vec::new();
        for item in &self.items {
            lines.push(format!(
                "{:<mw$} .{:<uw$}  {:<vw$} : {}",
                item.session_mnemonic(),
                item.unit(),
                item.value().display_str(),
                item.descr(),
                mw = mnem_w,
                uw = unit_w,
                vw = val_w,
            ));
        }
        lines.join("\n")
    }

    #[getter]
    fn json(&self) -> PyResult<String> {
        let arr: Vec<serde_json::Value> = self.items.iter().map(|item| {
            item.to_json_value()
        }).collect();
        Ok(serde_json::to_string(&arr).unwrap())
    }

    #[setter]
    fn set_json_section(&self, _val: &str) -> PyResult<()> {
        Err(pyo3::exceptions::PyException::new_err("Cannot set json property directly"))
    }

    fn __getnewargs_ex__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let items_list = PyList::new(py, self.items.iter().map(|item| item.to_py(py)))?;
        let args = PyTuple::new(py, &[items_list.into_any()])?;
        let kwargs = PyDict::new(py);
        kwargs.set_item("mnemonic_transforms", self.mnemonic_transforms)?;
        PyTuple::new(py, &[args.into_any(), kwargs.into_any()])
    }
}
