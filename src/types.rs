use numpy::{PyArray1, PyArrayMethods};
use pyo3::exceptions::{PyKeyError, PyIndexError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PySlice, PyTuple, PyBool, PyFloat, PyInt};

// ---------------------------------------------------------------------------
// Value
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub enum Value {
    Str(String),
    Int(i64),
    Float(f64),
}

impl Value {
    pub fn to_py(&self, py: Python<'_>) -> PyObject {
        match self {
            Value::Str(s) => s.into_pyobject(py).unwrap().into_any().unbind(),
            Value::Int(i) => i.into_pyobject(py).unwrap().into_any().unbind(),
            Value::Float(f) => f.into_pyobject(py).unwrap().into_any().unbind(),
        }
    }

    pub fn from_py(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
        // Handle None → empty string
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

    pub fn display_str(&self) -> String {
        match self {
            Value::Str(s) => s.clone(),
            Value::Int(i) => i.to_string(),
            Value::Float(f) => format_float(*f),
        }
    }

    pub fn to_json_value(&self) -> serde_json::Value {
        match self {
            Value::Str(s) => serde_json::Value::String(s.clone()),
            Value::Int(i) => serde_json::json!(*i),
            Value::Float(f) => serde_json::json!(*f),
        }
    }
}

impl Default for Value {
    fn default() -> Self {
        Value::Str(String::new())
    }
}

impl std::fmt::Display for Value {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Value::Str(s) => write!(f, "{}", s),
            Value::Int(i) => write!(f, "{}", i),
            Value::Float(v) => write!(f, "{}", format_float(*v)),
        }
    }
}

fn format_float(f: f64) -> String {
    if f == f.trunc() && f.abs() < 1e15 {
        // Display as integer-like: 8.0 -> "8.5" won't match, 8.0 -> "8.0"
        // Actually let's just use default Display which does the right thing
        format!("{}", f)
    } else {
        format!("{}", f)
    }
}

// ---------------------------------------------------------------------------
// HeaderItem
// ---------------------------------------------------------------------------

#[pyclass(subclass, module = "las_rs._native")]
#[derive(Debug, Clone)]
pub struct HeaderItem {
    pub original_mnemonic: String,
    pub session_mnemonic: String,
    pub unit: String,
    pub value: Value,
    pub descr: String,
    pub data: Value,
}

#[pymethods]
impl HeaderItem {
    #[new]
    #[pyo3(signature = (mnemonic="", unit="", value=None, descr="", data=None))]
    fn new(
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
            "useful_mnemonic" => Ok(self.useful_mnemonic().into_pyobject(py).unwrap().into_any().unbind()),
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

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<bool> {
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

#[pyclass(module = "las_rs._native")]
#[derive(Debug, Clone)]
pub struct CurveItem {
    pub header: HeaderItem,
    pub curve_data: Vec<f64>,
    pub string_data: Option<Vec<String>>,
    pub dtype_override: Option<String>, // "int", "str", etc.
}

#[pymethods]
impl CurveItem {
    #[new]
    #[pyo3(signature = (mnemonic="", unit="", value=None, descr="", data=None))]
    fn new(
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
            let arr = np.call_method1("array", (list,))?;
            return Ok(arr.unbind());
        }
        // Check for dtype override
        if let Some(ref dtype) = self.dtype_override {
            if dtype == "int" {
                let np = py.import("numpy")?;
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
            "useful_mnemonic" => Ok(self.useful_mnemonic().into_pyobject(py).unwrap().into_any().unbind()),
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
// ItemWrapper — internal enum to hold either HeaderItem or CurveItem
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub enum ItemWrapper {
    Header(HeaderItem),
    Curve(CurveItem),
}

impl ItemWrapper {
    pub fn session_mnemonic(&self) -> &str {
        match self {
            ItemWrapper::Header(h) => &h.session_mnemonic,
            ItemWrapper::Curve(c) => &c.header.session_mnemonic,
        }
    }

    pub fn original_mnemonic(&self) -> &str {
        match self {
            ItemWrapper::Header(h) => &h.original_mnemonic,
            ItemWrapper::Curve(c) => &c.header.original_mnemonic,
        }
    }

    pub fn set_session_mnemonic_only(&mut self, name: String) {
        match self {
            ItemWrapper::Header(h) => h.session_mnemonic = name,
            ItemWrapper::Curve(c) => c.header.session_mnemonic = name,
        }
    }

    pub fn value(&self) -> &Value {
        match self {
            ItemWrapper::Header(h) => &h.value,
            ItemWrapper::Curve(c) => &c.header.value,
        }
    }

    pub fn set_value(&mut self, val: Value) {
        match self {
            ItemWrapper::Header(h) => h.value = val,
            ItemWrapper::Curve(c) => c.header.value = val,
        }
    }

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
            Err(PyTypeError::new_err("Expected HeaderItem or CurveItem"))
        }
    }

    pub fn unit(&self) -> &str {
        match self {
            ItemWrapper::Header(h) => &h.unit,
            ItemWrapper::Curve(c) => &c.header.unit,
        }
    }

    pub fn descr(&self) -> &str {
        match self {
            ItemWrapper::Header(h) => &h.descr,
            ItemWrapper::Curve(c) => &c.header.descr,
        }
    }

    pub fn to_json_value(&self) -> serde_json::Value {
        match self {
            ItemWrapper::Header(h) => {
                let mut map = serde_json::Map::new();
                map.insert("mnemonic".to_string(), serde_json::Value::String(h.original_mnemonic.clone()));
                map.insert("unit".to_string(), serde_json::Value::String(h.unit.clone()));
                map.insert("value".to_string(), h.value.to_json_value());
                map.insert("descr".to_string(), serde_json::Value::String(h.descr.clone()));
                serde_json::Value::Object(map)
            }
            ItemWrapper::Curve(c) => {
                let mut map = serde_json::Map::new();
                map.insert("mnemonic".to_string(), serde_json::Value::String(c.header.original_mnemonic.clone()));
                map.insert("unit".to_string(), serde_json::Value::String(c.header.unit.clone()));
                map.insert("value".to_string(), c.header.value.to_json_value());
                map.insert("descr".to_string(), serde_json::Value::String(c.header.descr.clone()));
                let data_vals: Vec<serde_json::Value> = c.curve_data.iter().map(|v| {
                    if v.is_nan() { serde_json::Value::Null } else { serde_json::json!(*v) }
                }).collect();
                map.insert("data".to_string(), serde_json::Value::Array(data_vals));
                serde_json::Value::Object(map)
            }
        }
    }
}

// ---------------------------------------------------------------------------
// SectionItems
// ---------------------------------------------------------------------------

#[pyclass(module = "las_rs._native")]
#[derive(Debug, Clone)]
pub struct SectionItems {
    pub items: Vec<ItemWrapper>,
    #[pyo3(get, set)]
    pub mnemonic_transforms: bool,
}

impl SectionItems {
    fn compare_mnemonics(&self, a: &str, b: &str) -> bool {
        if self.mnemonic_transforms {
            a.eq_ignore_ascii_case(b)
        } else {
            a == b
        }
    }

    pub fn find_index_by_mnemonic(&self, mnemonic: &str) -> Option<usize> {
        self.items.iter().position(|item| {
            self.compare_mnemonics(item.session_mnemonic(), mnemonic)
        })
    }

    pub fn assign_duplicate_suffixes_for(&mut self, test_mnemonic: &str) {
        let case_insensitive = self.mnemonic_transforms;
        let matches = |orig: &str| -> bool {
            if case_insensitive {
                orig.eq_ignore_ascii_case(test_mnemonic)
            } else {
                orig == test_mnemonic
            }
        };

        // Count how many items have this original_mnemonic
        let count = self.items.iter()
            .filter(|item| matches(item.original_mnemonic()))
            .count();

        if count <= 1 {
            // If only one, restore session mnemonic to original
            for item in &mut self.items {
                if matches(item.original_mnemonic()) {
                    let orig = item.original_mnemonic().to_string();
                    item.set_session_mnemonic_only(orig);
                }
            }
            return;
        }

        // Multiple: assign :1, :2, :3, ...
        let mut counter = 0;
        for i in 0..self.items.len() {
            if matches(self.items[i].original_mnemonic()) {
                counter += 1;
                let new_name = format!("{}:{}", self.items[i].original_mnemonic(), counter);
                self.items[i].set_session_mnemonic_only(new_name);
            }
        }
    }

    pub fn assign_duplicate_suffixes_all(&mut self) {
        // Collect unique original mnemonics
        let mnemonics: Vec<String> = self.items.iter()
            .map(|item| item.original_mnemonic().to_string())
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        for m in mnemonics {
            self.assign_duplicate_suffixes_for(&m);
        }
    }
}

#[pymethods]
impl SectionItems {
    #[new]
    #[pyo3(signature = (items_or_transforms=None, mnemonic_transforms=true))]
    fn new(
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
        let wrapper = ItemWrapper::from_py(item)?;
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

        // Check if section contains CurveItems — if so, return a CurveItem with NaN data
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
