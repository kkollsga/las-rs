use numpy::{PyArray2, PyArrayMethods};
use pyo3::exceptions::{PyIOError, PyIndexError, PyKeyError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

use crate::core::helpers::natural_sort_key;
use crate::core::las_file::LASFile;
use crate::core::types::{CurveItem, HeaderItem, ItemWrapper, SectionItems, Value};
use crate::python::conversions::extract_curve_data;
use crate::reader;
use crate::writer;

#[pymethods]
impl LASFile {
    #[new]
    fn new() -> Self {
        let mut version = SectionItems {
            items: Vec::new(),
            mnemonic_transforms: true,
        };
        // Add default VERS and WRAP
        version.items.push(ItemWrapper::Header(HeaderItem {
            original_mnemonic: "VERS".to_string(),
            session_mnemonic: "VERS".to_string(),
            unit: String::new(),
            value: Value::Float(2.0),
            descr: "CWLS LOG ASCII STANDARD - VERSION 2.0".to_string(),
            data: Value::Str(String::new()),
        }));
        version.items.push(ItemWrapper::Header(HeaderItem {
            original_mnemonic: "WRAP".to_string(),
            session_mnemonic: "WRAP".to_string(),
            unit: String::new(),
            value: Value::Str("NO".to_string()),
            descr: "ONE LINE PER DEPTH STEP".to_string(),
            data: Value::Str(String::new()),
        }));

        LASFile {
            version_section: version,
            well_section: SectionItems { items: Vec::new(), mnemonic_transforms: true },
            curves_section: SectionItems { items: Vec::new(), mnemonic_transforms: true },
            params_section: SectionItems { items: Vec::new(), mnemonic_transforms: true },
            other_section: String::new(),
            custom_sections: HashMap::new(),
            encoding: None,
            index_unit: None,
        }
    }

    #[getter]
    fn get_encoding(&self) -> Option<&str> {
        self.encoding.as_deref()
    }

    #[setter]
    fn set_encoding(&mut self, val: Option<String>) {
        self.encoding = val;
    }

    #[getter]
    fn get_index_unit(&self) -> Option<&str> {
        self.index_unit.as_deref()
    }

    #[setter]
    fn set_index_unit(&mut self, val: Option<String>) {
        self.index_unit = val;
    }

    #[getter]
    fn version(&self, _py: Python<'_>) -> PyResult<SectionItems> {
        Ok(self.version_section.clone())
    }

    #[setter]
    fn set_version(&mut self, val: SectionItems) {
        self.version_section = val;
    }

    #[getter]
    fn well(&self) -> SectionItems {
        self.well_section.clone()
    }

    #[setter]
    fn set_well(&mut self, val: SectionItems) {
        self.well_section = val;
    }

    #[getter]
    fn curves(&self) -> SectionItems {
        self.curves_section.clone()
    }

    #[setter]
    fn set_curves(&mut self, val: SectionItems) {
        self.curves_section = val;
    }

    #[getter]
    fn params(&self) -> SectionItems {
        self.params_section.clone()
    }

    #[setter]
    fn set_params(&mut self, val: SectionItems) {
        self.params_section = val;
    }

    #[getter]
    fn other(&self) -> &str {
        &self.other_section
    }

    #[setter]
    fn set_other(&mut self, val: &str) {
        self.other_section = val.to_string();
    }

    #[getter]
    fn sections(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("Version", self.version_section.clone().into_pyobject(py)?)?;
        dict.set_item("Well", self.well_section.clone().into_pyobject(py)?)?;
        dict.set_item("Curves", self.curves_section.clone().into_pyobject(py)?)?;
        dict.set_item("Parameter", self.params_section.clone().into_pyobject(py)?)?;
        dict.set_item("Other", &self.other_section)?;
        for (key, sec) in &self.custom_sections {
            dict.set_item(key, sec.clone().into_pyobject(py)?)?;
        }
        Ok(dict.into_any().unbind())
    }

    #[getter]
    fn header(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.sections(py)
    }

    #[getter]
    fn data<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyArray2<f64>>> {
        // Stack all curve data arrays into a 2D array (n_rows x n_curves)
        let n_curves = self.curves_section.items.len();
        if n_curves == 0 {
            return Ok(PyArray2::from_vec2(py, &vec![]).unwrap());
        }

        // Get number of rows from first curve
        let n_rows = match &self.curves_section.items[0] {
            ItemWrapper::Curve(c) => c.curve_data.len(),
            _ => 0,
        };

        if n_rows == 0 {
            let empty: Vec<Vec<f64>> = Vec::new();
            return Ok(PyArray2::from_vec2(py, &empty).unwrap());
        }

        // Build row-major 2D array
        let mut rows: Vec<Vec<f64>> = Vec::with_capacity(n_rows);
        for row_idx in 0..n_rows {
            let mut row = Vec::with_capacity(n_curves);
            for item in &self.curves_section.items {
                match item {
                    ItemWrapper::Curve(c) => {
                        if row_idx < c.curve_data.len() {
                            row.push(c.curve_data[row_idx]);
                        } else {
                            row.push(f64::NAN);
                        }
                    }
                    _ => row.push(f64::NAN),
                }
            }
            rows.push(row);
        }

        Ok(PyArray2::from_vec2(py, &rows).unwrap())
    }

    #[setter]
    fn set_data(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.set_data_array(py, value, None, false)
    }

    #[getter]
    fn index<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        if let Some(ItemWrapper::Curve(c)) = self.curves_section.items.first() {
            Ok(numpy::PyArray1::from_vec(py, c.curve_data.clone()))
        } else {
            Ok(numpy::PyArray1::from_vec(py, vec![]))
        }
    }

    // ----- Curve manipulation -----

    #[pyo3(signature = (mnemonic, data=None, unit="", descr="", value=None))]
    fn append_curve(
        &mut self,
        _py: Python<'_>,
        mnemonic: &str,
        data: Option<&Bound<'_, PyAny>>,
        unit: &str,
        descr: &str,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let curve_data = extract_curve_data(data)?;
        let val = match value {
            Some(v) => Value::from_py(v)?,
            None => Value::Str(String::new()),
        };
        let item = CurveItem {
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
        };
        let orig = mnemonic.to_string();
        self.curves_section.items.push(ItemWrapper::Curve(item));
        self.curves_section.assign_duplicate_suffixes_for(&orig);
        Ok(())
    }

    #[pyo3(signature = (ix, mnemonic, data=None, unit="", descr="", value=None))]
    fn insert_curve(
        &mut self,
        _py: Python<'_>,
        ix: usize,
        mnemonic: &str,
        data: Option<&Bound<'_, PyAny>>,
        unit: &str,
        descr: &str,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let curve_data = extract_curve_data(data)?;
        let val = match value {
            Some(v) => Value::from_py(v)?,
            None => Value::Str(String::new()),
        };
        let item = CurveItem {
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
        };
        let idx = ix.min(self.curves_section.items.len());
        let orig = mnemonic.to_string();
        self.curves_section.items.insert(idx, ItemWrapper::Curve(item));
        self.curves_section.assign_duplicate_suffixes_for(&orig);
        Ok(())
    }

    #[pyo3(signature = (mnemonic=None, ix=None))]
    fn delete_curve(&mut self, mnemonic: Option<&str>, ix: Option<usize>) -> PyResult<()> {
        if let Some(index) = ix {
            if index < self.curves_section.items.len() {
                self.curves_section.items.remove(index);
                return Ok(());
            }
            return Err(PyIndexError::new_err("curve index out of range"));
        }
        if let Some(name) = mnemonic {
            if let Some(idx) = self.curves_section.find_index_by_mnemonic(name) {
                self.curves_section.items.remove(idx);
                return Ok(());
            }
            return Err(PyKeyError::new_err(name.to_string()));
        }
        Err(PyKeyError::new_err("must specify mnemonic or ix"))
    }

    fn get_curve(&self, py: Python<'_>, mnemonic: &str) -> PyResult<PyObject> {
        if let Some(idx) = self.curves_section.find_index_by_mnemonic(mnemonic) {
            return Ok(self.curves_section.items[idx].to_py(py));
        }
        Err(PyKeyError::new_err(mnemonic.to_string()))
    }

    fn append_curve_item(&mut self, item: &Bound<'_, PyAny>) -> PyResult<()> {
        let wrapper = ItemWrapper::from_py(item)?;
        let orig = wrapper.original_mnemonic().to_string();
        self.curves_section.items.push(wrapper);
        self.curves_section.assign_duplicate_suffixes_for(&orig);
        Ok(())
    }

    fn insert_curve_item(&mut self, ix: usize, item: &Bound<'_, PyAny>) -> PyResult<()> {
        let wrapper = ItemWrapper::from_py(item)?;
        let orig = wrapper.original_mnemonic().to_string();
        let idx = ix.min(self.curves_section.items.len());
        self.curves_section.items.insert(idx, wrapper);
        self.curves_section.assign_duplicate_suffixes_for(&orig);
        Ok(())
    }

    fn replace_curve_item(&mut self, ix: usize, item: &Bound<'_, PyAny>) -> PyResult<()> {
        if ix >= self.curves_section.items.len() {
            return Err(PyIndexError::new_err("curve index out of range"));
        }
        let wrapper = ItemWrapper::from_py(item)?;
        self.curves_section.items[ix] = wrapper;
        Ok(())
    }

    fn keys(&self) -> Vec<String> {
        self.curves_section.items.iter()
            .map(|item| item.session_mnemonic().to_string())
            .collect()
    }

    fn values(&self, py: Python<'_>) -> PyResult<Vec<PyObject>> {
        Ok(self.curves_section.items.iter()
            .map(|item| {
                if let ItemWrapper::Curve(c) = item {
                    numpy::PyArray1::from_vec(py, c.curve_data.clone()).into_any().unbind()
                } else {
                    py.None().into()
                }
            })
            .collect())
    }

    fn items(&self, py: Python<'_>) -> PyResult<Vec<(String, PyObject)>> {
        Ok(self.curves_section.items.iter()
            .map(|item| {
                let name = item.session_mnemonic().to_string();
                let data = if let ItemWrapper::Curve(c) = item {
                    numpy::PyArray1::from_vec(py, c.curve_data.clone()).into_any().unbind()
                } else {
                    py.None().into()
                };
                (name, data)
            })
            .collect())
    }

    #[pyo3(signature = (mnemonic=None, data=None, unit=None, descr=None, value=None, ix=None))]
    fn update_curve(
        &mut self,
        mnemonic: Option<&str>,
        data: Option<&Bound<'_, PyAny>>,
        unit: Option<&str>,
        descr: Option<&str>,
        value: Option<&Bound<'_, PyAny>>,
        ix: Option<usize>,
    ) -> PyResult<()> {
        let idx = if let Some(i) = ix {
            if i >= self.curves_section.items.len() {
                return Err(PyIndexError::new_err("curve index out of range"));
            }
            i
        } else if let Some(name) = mnemonic {
            self.curves_section.find_index_by_mnemonic(name)
                .ok_or_else(|| PyKeyError::new_err(name.to_string()))?
        } else {
            return Err(PyKeyError::new_err("must specify mnemonic or ix"));
        };

        if let ItemWrapper::Curve(ref mut c) = self.curves_section.items[idx] {
            if let Some(d) = data {
                c.curve_data = extract_curve_data(Some(d))?;
            }
            if let Some(u) = unit {
                c.header.unit = u.to_string();
            }
            if let Some(d) = descr {
                c.header.descr = d.to_string();
            }
            if let Some(v) = value {
                c.header.value = Value::from_py(v)?;
            }
        }
        Ok(())
    }

    #[getter]
    fn curvesdict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        for item in &self.curves_section.items {
            dict.set_item(item.session_mnemonic(), item.to_py(py))?;
        }
        Ok(dict.into_any().unbind())
    }

    #[pyo3(signature = (array, names=None, truncate=false), name = "set_data")]
    fn set_data_array(
        &mut self,
        py: Python<'_>,
        array: &Bound<'_, PyAny>,
        names: Option<Vec<String>>,
        truncate: bool,
    ) -> PyResult<()> {
        // Extract 2D array
        let np = py.import("numpy")?;
        let arr = np.call_method1("asarray", (array,))?;
        let shape: Vec<usize> = arr.getattr("shape")?.extract()?;

        if shape.len() != 2 {
            return Err(pyo3::exceptions::PyValueError::new_err("array must be 2D"));
        }
        let n_rows = shape[0];
        let n_cols = shape[1];

        // Extract columns using numpy indexing: arr[:, col_idx]
        for col_idx in 0..n_cols {
            let col_arr = arr.call_method1("__getitem__", (
                pyo3::types::PyTuple::new(py, &[
                    py.import("builtins")?.call_method1("slice", (py.None(), py.None()))?.into_any(),
                    col_idx.into_pyobject(py)?.into_any(),
                ])?,
            ))?;
            let col_data: Vec<f64> = col_arr.call_method0("tolist")?.extract()?;

            if col_idx < self.curves_section.items.len() {
                if let ItemWrapper::Curve(ref mut c) = self.curves_section.items[col_idx] {
                    c.curve_data = col_data;
                    if let Some(ref nm) = names {
                        if col_idx < nm.len() {
                            c.header.original_mnemonic = nm[col_idx].clone();
                            c.header.session_mnemonic = nm[col_idx].clone();
                        }
                    }
                }
            } else {
                let mnem = names.as_ref()
                    .and_then(|n| n.get(col_idx))
                    .cloned()
                    .unwrap_or_else(|| format!("Column{}", col_idx));
                let item = CurveItem {
                    header: HeaderItem {
                        original_mnemonic: mnem.clone(),
                        session_mnemonic: mnem,
                        unit: String::new(),
                        value: Value::Str(String::new()),
                        descr: String::new(),
                        data: Value::Str(String::new()),
                    },
                    curve_data: col_data,
                    string_data: None,
                    dtype_override: None,
                };
                self.curves_section.items.push(ItemWrapper::Curve(item));
            }
        }

        // Truncate excess curves if requested
        if truncate && n_cols < self.curves_section.items.len() {
            self.curves_section.items.truncate(n_cols);
        }

        Ok(())
    }

    #[pyo3(signature = (df, truncate=true))]
    fn set_data_from_df(&mut self, py: Python<'_>, df: &Bound<'_, PyAny>, truncate: bool) -> PyResult<()> {
        // Extract index as first curve
        let index_data: Vec<f64> = df.getattr("index")?.call_method0("tolist")?.extract()?;
        let index_name: String = df.getattr("index")?.getattr("name")?.extract().unwrap_or_else(|_| "DEPT".to_string());

        // Extract column data
        let columns: Vec<String> = df.getattr("columns")?.call_method0("tolist")?.extract()?;

        // Clear existing curves
        self.curves_section.items.clear();

        // Add index curve
        let index_item = CurveItem {
            header: HeaderItem {
                original_mnemonic: index_name.clone(),
                session_mnemonic: index_name,
                unit: String::new(),
                value: Value::Str(String::new()),
                descr: String::new(),
                data: Value::Str(String::new()),
            },
            curve_data: index_data,
            string_data: None,
            dtype_override: None,
        };
        self.curves_section.items.push(ItemWrapper::Curve(index_item));

        // Add column curves
        for col_name in &columns {
            let col_data: Vec<f64> = df.get_item(col_name)?
                .call_method0("tolist")?
                .extract()?;
            let item = CurveItem {
                header: HeaderItem {
                    original_mnemonic: col_name.clone(),
                    session_mnemonic: col_name.clone(),
                    unit: String::new(),
                    value: Value::Str(String::new()),
                    descr: String::new(),
                    data: Value::Str(String::new()),
                },
                curve_data: col_data,
                string_data: None,
                dtype_override: None,
            };
            self.curves_section.items.push(ItemWrapper::Curve(item));
        }

        Ok(())
    }

    fn __getitem__(&self, py: Python<'_>, key: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(idx) = key.extract::<isize>() {
            let len = self.curves_section.items.len() as isize;
            let actual = if idx < 0 { len + idx } else { idx };
            if actual < 0 || actual >= len {
                return Err(PyIndexError::new_err("index out of range"));
            }
            // Return data array, not CurveItem
            if let ItemWrapper::Curve(c) = &self.curves_section.items[actual as usize] {
                return Ok(numpy::PyArray1::from_vec(py, c.curve_data.clone()).into_any().unbind());
            }
        }
        if let Ok(name) = key.extract::<String>() {
            if let Some(idx) = self.curves_section.find_index_by_mnemonic(&name) {
                if let ItemWrapper::Curve(c) = &self.curves_section.items[idx] {
                    return Ok(numpy::PyArray1::from_vec(py, c.curve_data.clone()).into_any().unbind());
                }
            }
            return Err(PyKeyError::new_err(name));
        }
        Err(pyo3::exceptions::PyTypeError::new_err("key must be int or str"))
    }

    fn __setitem__(&mut self, py: Python<'_>, key: &Bound<'_, PyAny>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let name = key.extract::<String>()?;

        // If value is a CurveItem, replace or append
        if let Ok(ci) = value.extract::<CurveItem>() {
            // Validate: CurveItem mnemonic must match key
            if ci.header.original_mnemonic != name && ci.header.session_mnemonic != name {
                return Err(PyKeyError::new_err(format!(
                    "CurveItem mnemonic '{}' does not match key '{}'",
                    ci.header.original_mnemonic, name
                )));
            }
            if let Some(idx) = self.curves_section.find_index_by_mnemonic(&name) {
                self.curves_section.items[idx] = ItemWrapper::Curve(ci);
            } else {
                self.curves_section.items.push(ItemWrapper::Curve(ci));
            }
            return Ok(());
        }

        // Otherwise, treat as data array
        let data = extract_curve_data(Some(value))?;
        if let Some(idx) = self.curves_section.find_index_by_mnemonic(&name) {
            if let ItemWrapper::Curve(ref mut c) = self.curves_section.items[idx] {
                c.curve_data = data;
            }
        } else {
            // Append new curve
            let item = CurveItem {
                header: HeaderItem {
                    original_mnemonic: name.clone(),
                    session_mnemonic: name.clone(),
                    unit: String::new(),
                    value: Value::Str(String::new()),
                    descr: String::new(),
                    data: Value::Str(String::new()),
                },
                curve_data: data,
                string_data: None,
                dtype_override: None,
            };
            self.curves_section.items.push(ItemWrapper::Curve(item));
            self.curves_section.assign_duplicate_suffixes_for(&name);
        }
        Ok(())
    }

    // ----- DataFrame -----

    #[pyo3(signature = (include_units=false))]
    fn df(&self, py: Python<'_>, include_units: bool) -> PyResult<PyObject> {
        let pd = py.import("pandas")?;
        let data_dict = PyDict::new(py);

        for (i, item) in self.curves_section.items.iter().enumerate() {
            if let ItemWrapper::Curve(c) = item {
                let col_name = if include_units {
                    let unit = c.header.unit.as_str();
                    if unit.is_empty() {
                        c.header.original_mnemonic.clone()
                    } else {
                        format!("{} ({})", c.header.original_mnemonic, unit)
                    }
                } else {
                    c.header.original_mnemonic.clone()
                };

                if i == 0 {
                    continue; // index column, handled separately
                }
                if let Some(ref strings) = c.string_data {
                    // String column -> pandas Series with object dtype
                    let series = pd.call_method1("Series", (strings.clone(),))?;
                    let series = series.call_method1("astype", ("object",))?;
                    data_dict.set_item(col_name, series)?;
                } else {
                    let arr = numpy::PyArray1::from_vec(py, c.curve_data.clone());
                    data_dict.set_item(col_name, arr)?;
                }
            }
        }

        // Use first curve as index
        let index_data = match self.curves_section.items.first() {
            Some(ItemWrapper::Curve(c)) => c.curve_data.clone(),
            _ => vec![],
        };
        let index_arr = numpy::PyArray1::from_vec(py, index_data);

        let index_name = match self.curves_section.items.first() {
            Some(item) => {
                if include_units {
                    let unit = item.unit();
                    if unit.is_empty() {
                        item.original_mnemonic().to_string()
                    } else {
                        format!("{} ({})", item.original_mnemonic(), unit)
                    }
                } else {
                    item.original_mnemonic().to_string()
                }
            }
            None => String::new(),
        };

        let kwargs = PyDict::new(py);
        let pd_index = pd.call_method("Index", (index_arr,), Some(&{
            let kw = PyDict::new(py);
            kw.set_item("name", &index_name)?;
            kw
        }))?;
        kwargs.set_item("index", pd_index)?;

        let df = pd.call_method("DataFrame", (data_dict,), Some(&kwargs))?;
        Ok(df.unbind())
    }

    // ----- JSON -----

    #[getter]
    fn json(&self, py: Python<'_>) -> PyResult<String> {
        let mut root = serde_json::Map::new();

        // Metadata
        let mut metadata = serde_json::Map::new();
        // Version
        let mut version_items = serde_json::Map::new();
        for item in &self.version_section.items {
            version_items.insert(
                item.original_mnemonic().to_string(),
                item.to_json_value(),
            );
        }
        metadata.insert("Version".to_string(), serde_json::Value::Object(version_items));
        // Well
        let mut well_items = serde_json::Map::new();
        for item in &self.well_section.items {
            well_items.insert(
                item.original_mnemonic().to_string(),
                item.to_json_value(),
            );
        }
        metadata.insert("Well".to_string(), serde_json::Value::Object(well_items));
        // Curves
        let mut curve_items = serde_json::Map::new();
        for item in &self.curves_section.items {
            curve_items.insert(
                item.original_mnemonic().to_string(),
                item.to_json_value(),
            );
        }
        metadata.insert("Curves".to_string(), serde_json::Value::Object(curve_items));
        // Params
        if !self.params_section.items.is_empty() {
            let mut param_items = serde_json::Map::new();
            for item in &self.params_section.items {
                param_items.insert(
                    item.original_mnemonic().to_string(),
                    item.to_json_value(),
                );
            }
            metadata.insert("Parameter".to_string(), serde_json::Value::Object(param_items));
        }
        root.insert("metadata".to_string(), serde_json::Value::Object(metadata));

        // Data
        let mut data_obj = serde_json::Map::new();
        for item in &self.curves_section.items {
            if let ItemWrapper::Curve(c) = item {
                let vals: Vec<serde_json::Value> = c.curve_data.iter().map(|v| {
                    if v.is_nan() {
                        serde_json::Value::Null
                    } else {
                        serde_json::json!(*v)
                    }
                }).collect();
                data_obj.insert(
                    c.header.original_mnemonic.clone(),
                    serde_json::Value::Array(vals),
                );
            }
        }
        root.insert("data".to_string(), serde_json::Value::Object(data_obj));

        Ok(serde_json::to_string(&serde_json::Value::Object(root)).unwrap())
    }

    #[setter]
    fn set_json(&self, _val: &str) -> PyResult<()> {
        Err(pyo3::exceptions::PyException::new_err("Cannot set json property directly"))
    }

    // ----- Depth conversion -----

    #[getter]
    fn depth_m<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let index = match self.curves_section.items.first() {
            Some(ItemWrapper::Curve(c)) => c.curve_data.clone(),
            _ => return Ok(numpy::PyArray1::from_vec(py, vec![])),
        };

        match self.index_unit.as_deref() {
            Some("M") => Ok(numpy::PyArray1::from_vec(py, index)),
            Some("FT") => {
                let converted: Vec<f64> = index.iter().map(|v| v * 0.3048).collect();
                Ok(numpy::PyArray1::from_vec(py, converted))
            }
            Some(".1IN") => {
                let converted: Vec<f64> = index.iter().map(|v| (v / 120.0) * 0.3048).collect();
                Ok(numpy::PyArray1::from_vec(py, converted))
            }
            Some(u) => Err(crate::python::errors::LASUnknownUnitError::new_err(
                format!("Unknown depth unit: {}", u)
            )),
            None => Err(crate::python::errors::LASUnknownUnitError::new_err(
                "No index unit detected"
            )),
        }
    }

    #[getter]
    fn depth_ft<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let index = match self.curves_section.items.first() {
            Some(ItemWrapper::Curve(c)) => c.curve_data.clone(),
            _ => return Ok(numpy::PyArray1::from_vec(py, vec![])),
        };

        match self.index_unit.as_deref() {
            Some("FT") => Ok(numpy::PyArray1::from_vec(py, index)),
            Some("M") => {
                let converted: Vec<f64> = index.iter().map(|v| v / 0.3048).collect();
                Ok(numpy::PyArray1::from_vec(py, converted))
            }
            Some(".1IN") => {
                let converted: Vec<f64> = index.iter().map(|v| v / 120.0).collect();
                Ok(numpy::PyArray1::from_vec(py, converted))
            }
            Some(u) => Err(crate::python::errors::LASUnknownUnitError::new_err(
                format!("Unknown depth unit: {}", u)
            )),
            None => Err(crate::python::errors::LASUnknownUnitError::new_err(
                "No index unit detected"
            )),
        }
    }

    // ----- stack_curves -----

    #[pyo3(signature = (mnemonics, sort_curves=true))]
    fn stack_curves<'py>(
        &self,
        py: Python<'py>,
        mnemonics: &Bound<'_, PyAny>,
        sort_curves: bool,
    ) -> PyResult<Bound<'py, PyArray2<f64>>> {
        let mut matched: Vec<(String, Vec<f64>)> = Vec::new();

        if let Ok(stub) = mnemonics.extract::<String>() {
            if stub.is_empty() {
                return Err(pyo3::exceptions::PyValueError::new_err("Empty mnemonic stub"));
            }
            // Check if it's an exact match first
            if let Some(idx) = self.curves_section.find_index_by_mnemonic(&stub) {
                if let ItemWrapper::Curve(c) = &self.curves_section.items[idx] {
                    matched.push((c.header.session_mnemonic.clone(), c.curve_data.clone()));
                }
            } else {
                // Stub/prefix match: find all curves starting with this string
                for item in &self.curves_section.items {
                    let mnem = item.session_mnemonic();
                    if mnem.starts_with(&stub) || item.original_mnemonic().starts_with(&stub) {
                        if let ItemWrapper::Curve(c) = item {
                            matched.push((mnem.to_string(), c.curve_data.clone()));
                        }
                    }
                }
                if matched.is_empty() {
                    return Err(PyKeyError::new_err(format!("No curves matching '{}'", stub)));
                }
            }
        } else {
            let names: Vec<String> = mnemonics.extract::<Vec<String>>()?;
            if names.is_empty() {
                return Err(pyo3::exceptions::PyValueError::new_err("Empty list of curve names"));
            }
            // Check for empty strings in list
            for name in &names {
                if name.is_empty() {
                    return Err(pyo3::exceptions::PyValueError::new_err("Empty mnemonic in list"));
                }
            }
            for name in &names {
                if let Some(idx) = self.curves_section.find_index_by_mnemonic(name) {
                    if let ItemWrapper::Curve(c) = &self.curves_section.items[idx] {
                        matched.push((name.clone(), c.curve_data.clone()));
                    }
                } else {
                    return Err(PyKeyError::new_err(name.clone()));
                }
            }
        }

        if matched.is_empty() {
            return Ok(PyArray2::from_vec2(py, &vec![]).unwrap());
        }

        // Natural sort if requested
        if sort_curves {
            matched.sort_by(|a, b| natural_sort_key(&a.0).cmp(&natural_sort_key(&b.0)));
        }

        let arrays: Vec<&Vec<f64>> = matched.iter().map(|(_, d)| d).collect();
        let n_rows = arrays[0].len();
        let n_cols = arrays.len();
        let mut rows: Vec<Vec<f64>> = Vec::with_capacity(n_rows);
        for row_idx in 0..n_rows {
            let mut row = Vec::with_capacity(n_cols);
            for arr in &arrays {
                row.push(if row_idx < arr.len() { arr[row_idx] } else { f64::NAN });
            }
            rows.push(row);
        }

        Ok(PyArray2::from_vec2(py, &rows).unwrap())
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Pickle: write LAS to string, store as state
        let empty_map = HashMap::new();
        let output = writer::format_las(
            self,
            None, None, false, None, None, " ", "  ", None, &empty_map, None, None, None,
        )?;
        Ok(output.into_pyobject(py).unwrap().into_any().unbind())
    }

    fn __setstate__(&mut self, py: Python<'_>, state: &Bound<'_, PyAny>) -> PyResult<()> {
        let content: String = state.extract()?;
        let default_comments = vec!["#".to_string()];
        let restored = reader::read_las(&content, true, None, false, None, None, &default_comments)?;
        self.version_section = restored.version_section;
        self.well_section = restored.well_section;
        self.curves_section = restored.curves_section;
        self.params_section = restored.params_section;
        self.other_section = restored.other_section;
        self.custom_sections = restored.custom_sections;
        self.encoding = restored.encoding;
        self.index_unit = restored.index_unit;
        Ok(())
    }

    #[pyo3(signature = (STRT=None, STOP=None, STEP=None, fmt=None))]
    fn update_start_stop_step(
        &mut self,
        STRT: Option<f64>,
        STOP: Option<f64>,
        STEP: Option<f64>,
        fmt: Option<&str>,
    ) -> PyResult<()> {
        // Get index curve data
        let (index_data, index_unit) = match self.curves_section.items.first() {
            Some(ItemWrapper::Curve(c)) => (c.curve_data.clone(), c.header.unit.clone()),
            _ => return Ok(()),
        };

        if index_data.is_empty() {
            return Ok(());
        }

        let strt = STRT.unwrap_or(index_data[0]);
        let stop = STOP.unwrap_or(*index_data.last().unwrap());
        let step = STEP.unwrap_or_else(|| {
            if index_data.len() > 1 {
                (index_data[1] - index_data[0])
            } else {
                0.0
            }
        });

        // Update or create STRT, STOP, STEP in well section
        let updates = [("STRT", strt), ("STOP", stop), ("STEP", step)];
        for (name, val) in &updates {
            if let Some(idx) = self.well_section.find_index_by_mnemonic(name) {
                if let ItemWrapper::Header(ref mut h) = self.well_section.items[idx] {
                    h.value = Value::Float(*val);
                    h.unit = index_unit.clone();
                }
            }
        }

        Ok(())
    }

    #[pyo3(signature = (target, version=None, wrap=None, mnemonics_header=false, fmt=None, column_fmt=None, len_numeric_field=None, data_section_header=None, **kwargs))]
    fn write(
        &self,
        _py: Python<'_>,
        target: &Bound<'_, PyAny>,
        version: Option<f64>,
        wrap: Option<bool>,
        mnemonics_header: bool,
        fmt: Option<&str>,
        column_fmt: Option<&Bound<'_, PyAny>>,
        len_numeric_field: Option<i32>,
        data_section_header: Option<&str>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        // Extract formatting kwargs
        let lhs_spacer = kwargs
            .and_then(|kw| kw.get_item("lhs_spacer").ok().flatten())
            .and_then(|v| v.extract::<String>().ok())
            .unwrap_or_else(|| " ".to_string());
        let spacer = kwargs
            .and_then(|kw| kw.get_item("spacer").ok().flatten())
            .and_then(|v| v.extract::<String>().ok())
            .unwrap_or_else(|| "  ".to_string());
        let step_override = kwargs
            .and_then(|kw| kw.get_item("STEP").ok().flatten())
            .and_then(|v| v.extract::<f64>().ok());
        let strt_override = kwargs
            .and_then(|kw| kw.get_item("STRT").ok().flatten())
            .and_then(|v| v.extract::<f64>().ok());
        let stop_override = kwargs
            .and_then(|kw| kw.get_item("STOP").ok().flatten())
            .and_then(|v| v.extract::<f64>().ok());

        // Parse column_fmt dict
        let mut col_fmt_map: HashMap<usize, String> = HashMap::new();
        if let Some(cf) = column_fmt {
            if let Ok(dict) = cf.downcast::<PyDict>() {
                for (k, v) in dict.iter() {
                    if let (Ok(idx), Ok(fmt_str)) = (k.extract::<usize>(), v.extract::<String>()) {
                        col_fmt_map.insert(idx, fmt_str);
                    }
                }
            }
        }

        let output = writer::format_las(
            self,
            version, wrap, mnemonics_header, fmt, data_section_header,
            &lhs_spacer, &spacer, len_numeric_field, &col_fmt_map,
            step_override, strt_override, stop_override,
        )?;

        if let Ok(path) = target.extract::<String>() {
            std::fs::write(&path, &output)
                .map_err(|e| PyIOError::new_err(format!("Cannot write to {}: {}", path, e)))?;
        } else {
            target.call_method1("write", (&output,))?;
        }
        Ok(())
    }

    #[pyo3(signature = (target, mnemonics=None, units=None, units_loc=None, **kwargs))]
    fn to_csv(
        &self,
        py: Python<'_>,
        target: &Bound<'_, PyAny>,
        mnemonics: Option<&Bound<'_, PyAny>>,
        units: Option<&Bound<'_, PyAny>>,
        units_loc: Option<&str>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        let lineterminator = kwargs
            .and_then(|kw| kw.get_item("lineterminator").ok().flatten())
            .and_then(|v| v.extract::<String>().ok())
            .unwrap_or_else(|| "\n".to_string());

        // Extract mnemonics
        let mnem_list: Option<Vec<String>> = match mnemonics {
            Some(m) => m.extract::<Vec<String>>().ok(),
            None => None,
        };

        // Extract units
        let mut no_units = false;
        let unit_list: Option<Vec<String>> = match units {
            Some(u) => {
                if let Ok(false_val) = u.extract::<bool>() {
                    if !false_val { no_units = true; None } else { None }
                } else {
                    u.extract::<Vec<String>>().ok()
                }
            }
            None => None,
        };

        // Determine effective units_loc
        let effective_units_loc = if units_loc.is_none() && units.is_some() && !no_units {
            if units.and_then(|u| u.extract::<bool>().ok()).unwrap_or(false) {
                None // units=True without loc means no change
            } else if units.and_then(|u| u.extract::<Vec<String>>().ok()).is_some() {
                Some("line") // explicit list -> default to "line"
            } else {
                units_loc
            }
        } else {
            units_loc
        };

        let output = writer::format_csv(
            self,
            mnem_list.as_deref(),
            unit_list.as_deref(),
            effective_units_loc,
            &lineterminator,
            no_units,
        )?;

        if let Ok(path) = target.extract::<String>() {
            std::fs::write(&path, &output)
                .map_err(|e| PyIOError::new_err(format!("Cannot write to {}: {}", path, e)))?;
        } else {
            target.call_method1("write", (&output,))?;
        }
        Ok(())
    }
}
