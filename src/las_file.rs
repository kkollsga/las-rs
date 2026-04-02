use numpy::{PyArray1, PyArray2, PyArrayMethods};
use pyo3::exceptions::{PyIOError, PyIndexError, PyKeyError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

use crate::errors::LASHeaderError;
use crate::reader::data;
use crate::reader::header::{self, ValueType};
use crate::reader::sections::{self, SectionKind, SectionRange};
use crate::types::{CurveItem, HeaderItem, ItemWrapper, SectionItems, Value};

// ---------------------------------------------------------------------------
// Kwargs helpers — centralized extraction to avoid repetition
// ---------------------------------------------------------------------------

fn kwarg_string<'a>(kwargs: Option<&'a Bound<'_, PyDict>>, key: &str, default: &str) -> String {
    kwargs
        .and_then(|kw| kw.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<String>().ok())
        .unwrap_or_else(|| default.to_string())
}

fn kwarg_f64(kwargs: Option<&Bound<'_, PyDict>>, key: &str) -> Option<f64> {
    kwargs
        .and_then(|kw| kw.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<f64>().ok())
}

fn kwarg_bool(kwargs: Option<&Bound<'_, PyDict>>, key: &str, default: bool) -> bool {
    kwargs
        .and_then(|kw| kw.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<bool>().ok())
        .unwrap_or(default)
}

fn kwarg_opt_string(kwargs: Option<&Bound<'_, PyDict>>, key: &str) -> Option<String> {
    kwargs
        .and_then(|kw| kw.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<String>().ok())
}

// ---------------------------------------------------------------------------

fn extract_curve_data(data: Option<&Bound<'_, PyAny>>) -> PyResult<Vec<f64>> {
    match data {
        Some(d) => {
            if let Ok(arr) = d.extract::<Vec<f64>>() {
                Ok(arr)
            } else if let Ok(arr_ref) = d.downcast::<PyArray1<f64>>() {
                arr_ref.to_vec().map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("{}", e)))
            } else {
                Ok(Vec::new())
            }
        }
        None => Ok(Vec::new()),
    }
}

#[pyclass(module = "las_rs._native")]
#[derive(Debug, Clone)]
pub struct LASFile {
    pub version_section: SectionItems,
    pub well_section: SectionItems,
    pub curves_section: SectionItems,
    pub params_section: SectionItems,
    pub other_section: String,
    pub custom_sections: HashMap<String, SectionItems>,
    #[pyo3(get, set)]
    pub encoding: Option<String>,
    #[pyo3(get, set)]
    pub index_unit: Option<String>,
}

impl LASFile {
    pub fn create_default() -> Self {
        let mut version = SectionItems {
            items: Vec::new(),
            mnemonic_transforms: true,
        };
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
}

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
    fn version(&self, py: Python<'_>) -> PyResult<SectionItems> {
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
        py: Python<'_>,
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
        };
        let orig = mnemonic.to_string();
        self.curves_section.items.push(ItemWrapper::Curve(item));
        self.curves_section.assign_duplicate_suffixes_for(&orig);
        Ok(())
    }

    #[pyo3(signature = (ix, mnemonic, data=None, unit="", descr="", value=None))]
    fn insert_curve(
        &mut self,
        py: Python<'_>,
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
                    // String column → pandas object dtype
                    let list = pyo3::types::PyList::new(py, strings.iter().map(|s| s.as_str()))?;
                    data_dict.set_item(col_name, list)?;
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
            Some(u) => Err(crate::errors::LASUnknownUnitError::new_err(
                format!("Unknown depth unit: {}", u)
            )),
            None => Err(crate::errors::LASUnknownUnitError::new_err(
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
            Some(u) => Err(crate::errors::LASUnknownUnitError::new_err(
                format!("Unknown depth unit: {}", u)
            )),
            None => Err(crate::errors::LASUnknownUnitError::new_err(
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
        let output = self.format_las_full(
            None, None, false, None, None, " ", "  ", None, &empty_map, None, None, None,
        )?;
        Ok(output.into_pyobject(py).unwrap().into_any().unbind())
    }

    fn __setstate__(&mut self, py: Python<'_>, state: &Bound<'_, PyAny>) -> PyResult<()> {
        let content: String = state.extract()?;
        let default_comments = vec!["#".to_string()];
        let restored = read_las(&content, true, None, false, None, None, &default_comments)?;
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

        let output = self.format_las_full(
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
        let output = self.format_csv(mnemonics, units, units_loc, py, &lineterminator)?;

        if let Ok(path) = target.extract::<String>() {
            std::fs::write(&path, &output)
                .map_err(|e| PyIOError::new_err(format!("Cannot write to {}: {}", path, e)))?;
        } else {
            target.call_method1("write", (&output,))?;
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Writer implementation
// ---------------------------------------------------------------------------

impl LASFile {
    fn format_las_full(
        &self,
        version_override: Option<f64>,
        wrap_override: Option<bool>,
        mnemonics_header: bool,
        fmt: Option<&str>,
        data_section_header: Option<&str>,
        lhs_spacer: &str,
        spacer: &str,
        len_numeric_field: Option<i32>,
        column_fmt: &HashMap<usize, String>,
        step_override: Option<f64>,
        strt_override: Option<f64>,
        stop_override: Option<f64>,
    ) -> PyResult<String> {
        // Pre-allocate buffer based on estimated output size
        let n_curves = self.curves_section.items.len();
        let n_rows = self.curves_section.items.first()
            .and_then(|item| if let ItemWrapper::Curve(c) = item { Some(c.curve_data.len()) } else { None })
            .unwrap_or(0);
        let estimated = 2000 + n_rows * n_curves * 15; // header + data
        let mut out = String::with_capacity(estimated);

        let fmt_str = fmt.unwrap_or("%.5f");
        let precision = parse_fmt_precision(fmt_str);

        // Get NULL value
        let null_value = self.well_section.find_index_by_mnemonic("NULL")
            .map(|idx| {
                let item: &ItemWrapper = &self.well_section.items[idx];
                item.value().display_str().parse::<f64>().unwrap_or(-999.25)
            })
            .unwrap_or(-999.25);

        // Determine version for output
        let write_version = match version_override {
            Some(v) => v,
            None => {
                match self.version_section.find_index_by_mnemonic("VERS") {
                    Some(idx) => {
                        let item: &ItemWrapper = &self.version_section.items[idx];
                        item.value().display_str().parse::<f64>().unwrap_or(2.0)
                    }
                    None => {
                        return Err(crate::errors::LASHeaderError::new_err(
                            "Cannot write: VERS item missing from version section and no version override specified"
                        ));
                    }
                }
            }
        };

        // Validate WRAP exists if no override
        if wrap_override.is_none() && self.version_section.find_index_by_mnemonic("WRAP").is_none() {
            return Err(crate::errors::LASHeaderError::new_err(
                "Cannot write: WRAP item missing from version section and no wrap override specified"
            ));
        }

        // ~Version
        out.push_str("~Version ---------------------------------------------------\n");
        if version_override.is_some() {
            // Write overridden version
            out.push_str(&format!("VERS.   {:.1} : CWLS LOG ASCII STANDARD - VERSION {:.1}\n", write_version, write_version));
        } else {
            for item in &self.version_section.items {
                if item.original_mnemonic().to_uppercase() == "VERS" && version_override.is_some() {
                    continue; // skip, already written
                }
                write_header_item(&mut out, item);
            }
        }
        if version_override.is_some() {
            // Also write WRAP
            for item in &self.version_section.items {
                if item.original_mnemonic().to_uppercase() != "VERS" {
                    write_header_item(&mut out, item);
                }
            }
        }

        // ~Well — apply STRT/STOP/STEP overrides and auto-recalculate
        out.push_str("~Well ------------------------------------------------------\n");
        // Get actual depth range for STOP recalculation
        let actual_stop = self.curves_section.items.first().and_then(|item| {
            if let ItemWrapper::Curve(c) = item {
                c.curve_data.last().copied()
            } else { None }
        });
        for item in &self.well_section.items {
            let mnem_upper = item.original_mnemonic().to_uppercase();
            if mnem_upper == "STRT" && strt_override.is_some() {
                out.push_str(&format!(" {}.{}  {} : {}\n",
                    item.original_mnemonic(), item.unit(),
                    format!("{:.5}", strt_override.unwrap()), item.descr()));
            } else if mnem_upper == "STOP" {
                let stop_val = stop_override.or(actual_stop);
                if let Some(sv) = stop_val {
                    out.push_str(&format!(" {}.{}  {} : {}\n",
                        item.original_mnemonic(), item.unit(),
                        format!("{:.5}", sv), item.descr()));
                } else {
                    write_header_item(&mut out, item);
                }
            } else if mnem_upper == "STEP" && step_override.is_some() {
                out.push_str(&format!(" {}.{}  {} : {}\n",
                    item.original_mnemonic(), item.unit(),
                    format!("{:.5}", step_override.unwrap()), item.descr()));
            } else {
                write_header_item(&mut out, item);
            }
        }

        // ~Curves
        out.push_str("~Curves ----------------------------------------------------\n");
        for item in &self.curves_section.items {
            write_header_item(&mut out, item);
        }

        // ~Params (if any)
        if !self.params_section.items.is_empty() {
            out.push_str("~Params ----------------------------------------------------\n");
            for item in &self.params_section.items {
                write_header_item(&mut out, item);
            }
        }

        // ~Other (if any)
        if !self.other_section.trim().is_empty() {
            out.push_str("~Other -----------------------------------------------------\n");
            out.push_str(&self.other_section);
            if !self.other_section.ends_with('\n') {
                out.push('\n');
            }
        }

        // ~ASCII
        let header = data_section_header.unwrap_or("~ASCII -----------------------------------------------------");
        out.push_str(header);
        out.push('\n');

        if mnemonics_header {
            // Write curve names as a comment line
            let names: Vec<&str> = self.curves_section.items.iter()
                .map(|item| item.original_mnemonic())
                .collect();
            out.push_str(&format!(" {}\n", names.join("        ")));
        }

        // Write data
        let n_curves = self.curves_section.items.len();
        if n_curves > 0 {
            let n_rows = match &self.curves_section.items[0] {
                ItemWrapper::Curve(c) => c.curve_data.len(),
                _ => 0,
            };

            let should_wrap = wrap_override.unwrap_or(false);

            for row_idx in 0..n_rows {
                let mut vals = Vec::new();
                for (col_idx, item) in self.curves_section.items.iter().enumerate() {
                    if let ItemWrapper::Curve(c) = item {
                        let v = if row_idx < c.curve_data.len() {
                            c.curve_data[row_idx]
                        } else {
                            f64::NAN
                        };

                        // Determine precision for this column
                        let col_prec = if let Some(cf) = column_fmt.get(&col_idx) {
                            parse_fmt_precision(cf)
                        } else {
                            precision
                        };

                        let formatted = if v.is_nan() {
                            format!("{:.prec$}", null_value, prec = col_prec)
                        } else {
                            format!("{:.prec$}", v, prec = col_prec)
                        };

                        // Apply len_numeric_field padding
                        let padded = match len_numeric_field {
                            Some(w) if w > 0 => format!("{:>width$}", formatted, width = w as usize),
                            Some(-1) => formatted, // No padding
                            _ => formatted,
                        };

                        vals.push(padded);
                    }
                }

                if should_wrap {
                    // Wrapped mode: depth on its own line, then remaining values
                    if !vals.is_empty() {
                        out.push_str(&format!(" {}\n", vals[0]));
                        let remaining: Vec<&str> = vals[1..].iter().map(|s| s.as_str()).collect();
                        // Write remaining values, wrapping at ~80 chars
                        let mut line = String::from(" ");
                        for (i, val) in remaining.iter().enumerate() {
                            if line.len() + val.len() + 1 > 79 && i > 0 {
                                out.push_str(&line);
                                out.push('\n');
                                line = String::from(" ");
                            }
                            line.push_str(val);
                            if i < remaining.len() - 1 {
                                line.push_str("  ");
                            }
                        }
                        if line.trim().len() > 0 {
                            out.push_str(&line);
                            out.push('\n');
                        }
                    }
                } else {
                    out.push_str(&format!("{}{}\n", lhs_spacer, vals.join(spacer)));
                }
            }
        }

        Ok(out)
    }

    fn format_csv(
        &self,
        mnemonics: Option<&Bound<'_, PyAny>>,
        units: Option<&Bound<'_, PyAny>>,
        units_loc: Option<&str>,
        py: Python<'_>,
        lineterminator: &str,
    ) -> PyResult<String> {
        let mut out = String::new();

        // Determine column names
        let default_names: Vec<String> = self.curves_section.items.iter()
            .map(|item| item.original_mnemonic().to_string())
            .collect();

        let col_names: Vec<String> = match mnemonics {
            Some(m) => {
                if let Ok(list) = m.extract::<Vec<String>>() {
                    list
                } else {
                    default_names.clone()
                }
            }
            None => default_names.clone(),
        };

        // Get units
        let curve_units: Vec<String> = self.curves_section.items.iter()
            .map(|item| item.unit().to_string())
            .collect();

        let unit_strings: Vec<String> = match units {
            Some(u) => {
                if let Ok(false_val) = u.extract::<bool>() {
                    if !false_val { vec![] } else { curve_units.clone() }
                } else if let Ok(list) = u.extract::<Vec<String>>() {
                    list
                } else {
                    curve_units.clone()
                }
            }
            None => curve_units.clone(),
        };

        // If units explicitly provided but no units_loc, default to "line"
        let effective_units_loc = if units_loc.is_none() && units.is_some() && !unit_strings.is_empty() {
            // Check if units was explicitly a list (not just True)
            if units.and_then(|u| u.extract::<bool>().ok()).unwrap_or(false) {
                None // units=True without loc means no change
            } else if units.and_then(|u| u.extract::<Vec<String>>().ok()).is_some() {
                Some("line") // explicit list → default to "line"
            } else {
                units_loc
            }
        } else {
            units_loc
        };

        // Build header based on units_loc
        match effective_units_loc {
            Some("[]") => {
                let headers: Vec<String> = col_names.iter().enumerate().map(|(i, name)| {
                    if i < unit_strings.len() && !unit_strings[i].is_empty() {
                        format!("{}[{}]", name, unit_strings[i])
                    } else {
                        name.clone()
                    }
                }).collect();
                out.push_str(&headers.join(","));
                out.push_str(lineterminator);
            }
            Some("()") => {
                let headers: Vec<String> = col_names.iter().enumerate().map(|(i, name)| {
                    if i < unit_strings.len() && !unit_strings[i].is_empty() {
                        format!("{}({})", name, unit_strings[i])
                    } else {
                        name.clone()
                    }
                }).collect();
                out.push_str(&headers.join(","));
                out.push_str(lineterminator);
            }
            Some("line") => {
                // Mnemonic header
                out.push_str(&col_names.join(","));
                out.push_str(lineterminator);
                // Unit header
                out.push_str(&unit_strings.join(","));
                out.push_str(lineterminator);
            }
            _ => {
                // Default: just mnemonics
                out.push_str(&col_names.join(","));
                out.push_str(lineterminator);
            }
        }

        // Data rows
        let n_curves = self.curves_section.items.len();
        if n_curves > 0 {
            let n_rows = match &self.curves_section.items[0] {
                ItemWrapper::Curve(c) => c.curve_data.len(),
                _ => 0,
            };
            for row_idx in 0..n_rows {
                let mut vals = Vec::new();
                for item in &self.curves_section.items {
                    if let ItemWrapper::Curve(c) = item {
                        let v = if row_idx < c.curve_data.len() {
                            c.curve_data[row_idx]
                        } else {
                            f64::NAN
                        };
                        if v.is_nan() {
                            vals.push(String::new());
                        } else {
                            vals.push(format!("{}", v));
                        }
                    }
                }
                out.push_str(&vals.join(","));
                out.push_str(lineterminator);
            }
        }

        Ok(out)
    }
}

fn natural_sort_key(s: &str) -> Vec<(bool, u64, String)> {
    let mut parts = Vec::new();
    let mut num_buf = String::new();
    let mut str_buf = String::new();

    for ch in s.chars() {
        if ch.is_ascii_digit() {
            if !str_buf.is_empty() {
                parts.push((false, 0u64, str_buf.clone()));
                str_buf.clear();
            }
            num_buf.push(ch);
        } else {
            if !num_buf.is_empty() {
                let n = num_buf.parse::<u64>().unwrap_or(0);
                parts.push((true, n, String::new()));
                num_buf.clear();
            }
            str_buf.push(ch);
        }
    }
    if !num_buf.is_empty() {
        let n = num_buf.parse::<u64>().unwrap_or(0);
        parts.push((true, n, String::new()));
    }
    if !str_buf.is_empty() {
        parts.push((false, 0, str_buf));
    }
    parts
}

fn write_header_item(out: &mut String, item: &ItemWrapper) {
    let mnemonic = item.original_mnemonic();
    let unit = item.unit();
    let value = item.value().display_str();
    let descr = item.descr();
    out.push_str(&format!(" {}.{}  {} : {}\n", mnemonic, unit, value, descr));
}

fn parse_fmt_precision(fmt: &str) -> usize {
    // Parse "%.5f" → 5
    if let Some(start) = fmt.find('.') {
        let rest = &fmt[start + 1..];
        let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
        digits.parse::<usize>().unwrap_or(5)
    } else {
        5
    }
}

// ---------------------------------------------------------------------------
// read() implementation
// ---------------------------------------------------------------------------

pub fn read_las(
    content: &str,
    ignore_header_errors: bool,
    mnemonic_case: Option<&str>,
    ignore_data: bool,
    null_policy: Option<data::NullPolicy>,
    read_policy: Option<String>,
    ignore_comments: &[String],
) -> PyResult<LASFile> {
    let lines: Vec<&str> = content.lines().collect();

    // Section discovery
    let section_ranges = sections::discover_sections(&lines);

    if section_ranges.is_empty() {
        return Err(PyKeyError::new_err("No ~ sections found in LAS file"));
    }

    let mut las = LASFile::create_default();
    // Clear default version items — we'll rebuild from file
    las.version_section.items.clear();

    // Detect LAS version, WRAP, and delimiter in first pass
    let mut las_version = 2.0f64;
    let mut null_value = -999.25f64;
    let mut delimiter: Option<char> = None;
    let mut wrapped = false;

    for sec in &section_ranges {
        if sec.kind == SectionKind::Version {
            for line_idx in sec.start_line..sec.end_line {
                if let Some(parsed) = header::parse_header_line(lines[line_idx]) {
                    let upper = parsed.mnemonic.to_uppercase();
                    if upper == "VERS" {
                        if let Ok(v) = parsed.value.trim().parse::<f64>() {
                            las_version = v;
                        }
                    }
                    if upper == "WRAP" {
                        let wrap_val = parsed.value.trim().to_uppercase();
                        wrapped = wrap_val == "YES";
                    }
                    if upper == "DLM" {
                        let dlm_upper = parsed.value.trim().to_uppercase();
                        if dlm_upper == "COMMA" {
                            delimiter = Some(',');
                        } else if dlm_upper == "TAB" {
                            delimiter = Some('\t');
                        }
                    }
                }
            }
        }
    }

    let _is_v12 = las_version < 2.0;
    let effective_null_policy = null_policy.unwrap_or(data::NullPolicy::Strict);
    let mut string_col_indices: Vec<usize> = Vec::new();

    // Second pass: parse all sections
    for sec in &section_ranges {
        match &sec.kind {
            SectionKind::Version => {
                parse_header_section(&lines, sec, &mut las.version_section, false, ignore_header_errors)?;
            }
            SectionKind::Well => {
                parse_header_section(&lines, sec, &mut las.well_section, true, ignore_header_errors)?;
                // Extract NULL value
                if let Some(idx) = las.well_section.find_index_by_mnemonic("NULL") {
                    let item: &ItemWrapper = &las.well_section.items[idx];
                    let val_str = item.value().display_str();
                    if let Ok(v) = val_str.parse::<f64>() {
                        null_value = v;
                    }
                }
            }
            SectionKind::Curves => {
                let string_cols = parse_curve_section(&lines, sec, &mut las.curves_section, ignore_header_errors)?;
                // Store for data parsing
                string_col_indices = string_cols;
            }
            SectionKind::Parameter => {
                parse_header_section(&lines, sec, &mut las.params_section, true, ignore_header_errors)?;
            }
            SectionKind::Other => {
                let mut text_lines = Vec::new();
                for line_idx in sec.start_line..sec.end_line {
                    text_lines.push(lines[line_idx]);
                }
                las.other_section = text_lines.join("\n");
            }
            SectionKind::Data => {
                if !ignore_data {
                    let data_lines: Vec<&str> = (sec.start_line..sec.end_line)
                        .map(|i| lines[i])
                        .collect();
                    let n_curves = las.curves_section.items.len();

                    if !string_col_indices.is_empty() {
                        // Parse with string column support
                        let (float_cols, str_cols) = data::parse_data_section_with_strings(
                            &data_lines, n_curves, null_value, delimiter,
                            &string_col_indices,
                        );
                        assign_data_to_curves(&mut las.curves_section, float_cols, n_curves);
                        // Assign string data to string columns
                        for (&col_idx, strings) in &str_cols {
                            if col_idx < las.curves_section.items.len() {
                                if let ItemWrapper::Curve(ref mut c) = las.curves_section.items[col_idx] {
                                    c.string_data = Some(strings.clone());
                                }
                            }
                        }
                    } else {
                        let parsed = data::parse_data_section_with_policy(
                            &data_lines, n_curves, null_value, delimiter,
                            wrapped, &effective_null_policy,
                            read_policy.as_deref(), ignore_comments,
                        );
                        assign_data_to_curves(&mut las.curves_section, parsed.float_columns, n_curves);
                        // Assign auto-detected string data to curves
                        for (&col_idx, strings) in &parsed.string_columns {
                            if col_idx < las.curves_section.items.len() {
                                if let ItemWrapper::Curve(ref mut c) = las.curves_section.items[col_idx] {
                                    c.string_data = Some(strings.clone());
                                }
                            }
                        }
                    }
                }
            }
            SectionKind::Custom(title) => {
                let mut custom_sec = SectionItems {
                    items: Vec::new(),
                    mnemonic_transforms: true,
                };
                parse_header_section(&lines, sec, &mut custom_sec, false, ignore_header_errors)?;
                las.custom_sections.insert(title.clone(), custom_sec);
            }
        }
    }

    // Apply mnemonic_case transformation
    if let Some(case) = mnemonic_case {
        apply_mnemonic_case(&mut las, case);
    }

    // Detect index unit
    las.index_unit = detect_index_unit(&las);

    Ok(las)
}

fn parse_header_section(
    lines: &[&str],
    sec: &SectionRange,
    section: &mut SectionItems,
    parse_numeric_values: bool,
    ignore_header_errors: bool,
) -> PyResult<()> {
    for line_idx in sec.start_line..sec.end_line {
        let line = lines[line_idx];
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        match header::parse_header_line(line) {
            Some(parsed) => {
                let value = if parse_numeric_values {
                    match header::parse_value(&parsed.value, &parsed.mnemonic) {
                        ValueType::Int(i) => Value::Int(i),
                        ValueType::Float(f) => Value::Float(f),
                        ValueType::Str(s) => Value::Str(s),
                    }
                } else {
                    match header::parse_value(&parsed.value, &parsed.mnemonic) {
                        ValueType::Int(i) => Value::Int(i),
                        ValueType::Float(f) => Value::Float(f),
                        ValueType::Str(s) => Value::Str(s),
                    }
                };

                let mnemonic = if parsed.mnemonic.is_empty() {
                    "UNKNOWN".to_string()
                } else {
                    parsed.mnemonic
                };

                let item = HeaderItem {
                    original_mnemonic: mnemonic.clone(),
                    session_mnemonic: mnemonic.clone(),
                    unit: parsed.unit,
                    value,
                    descr: parsed.descr,
                    data: Value::Str(String::new()),
                };
                let orig = item.original_mnemonic.clone();
                section.items.push(ItemWrapper::Header(item));
                section.assign_duplicate_suffixes_for(&orig);
            }
            None => {
                if !ignore_header_errors && !trimmed.is_empty() && !trimmed.starts_with('#') {
                    return Err(LASHeaderError::new_err(format!(
                        "Failed to parse header line: {}", trimmed
                    )));
                }
            }
        }
    }
    Ok(())
}

fn parse_curve_section(
    lines: &[&str],
    sec: &SectionRange,
    section: &mut SectionItems,
    ignore_header_errors: bool,
) -> PyResult<Vec<usize>> {
    let mut string_col_indices = Vec::new();
    let mut curve_idx = 0usize;
    for line_idx in sec.start_line..sec.end_line {
        let line = lines[line_idx];
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        match header::parse_header_line(line) {
            Some(parsed) => {
                // Check for {S} format code indicating string column
                let is_string_col = parsed.value.contains("{S}") || parsed.descr.contains("{S}");
                let value_clean = if is_string_col {
                    let v = parsed.value.replace("{S}", "").trim().to_string();
                    match header::parse_value(&v, &parsed.mnemonic) {
                        ValueType::Int(i) => Value::Int(i),
                        ValueType::Float(f) => Value::Float(f),
                        ValueType::Str(s) => Value::Str(s),
                    }
                } else {
                    match header::parse_value(&parsed.value, &parsed.mnemonic) {
                        ValueType::Int(i) => Value::Int(i),
                        ValueType::Float(f) => Value::Float(f),
                        ValueType::Str(s) => Value::Str(s),
                    }
                };

                if is_string_col {
                    string_col_indices.push(curve_idx);
                }

                let mnemonic = if parsed.mnemonic.is_empty() {
                    "UNKNOWN".to_string()
                } else {
                    parsed.mnemonic
                };

                let item = CurveItem {
                    header: HeaderItem {
                        original_mnemonic: mnemonic.clone(),
                        session_mnemonic: mnemonic.clone(),
                        unit: parsed.unit,
                        value: value_clean,
                        descr: parsed.descr.replace("{S}", "").trim().to_string(),
                        data: Value::Str(String::new()),
                    },
                    curve_data: Vec::new(),
                    string_data: None,
                };
                let orig = item.header.original_mnemonic.clone();
                section.items.push(ItemWrapper::Curve(item));
                section.assign_duplicate_suffixes_for(&orig);
                curve_idx += 1;
            }
            None => {
                if !ignore_header_errors {
                    // skip
                }
            }
        }
    }
    Ok(string_col_indices)
}

fn assign_data_to_curves(curves_section: &mut SectionItems, columns: Vec<Vec<f64>>, n_declared: usize) {
    let n_data_cols = columns.len();
    let n_rows = if columns.is_empty() { 0 } else { columns[0].len() };

    // Assign data to declared curves
    for (i, item) in curves_section.items.iter_mut().enumerate() {
        if let ItemWrapper::Curve(ref mut c) = item {
            if i < n_data_cols {
                c.curve_data = columns[i].clone();
            } else {
                // Sparse curve: fill with NaN
                c.curve_data = vec![f64::NAN; n_rows];
            }
        }
    }

    // Handle excess data columns (more data than declared curves)
    if n_data_cols > n_declared {
        for col_idx in n_declared..n_data_cols {
            let mnemonic = format!("UNKNOWN_{}", col_idx - n_declared + 1);
            let item = CurveItem {
                header: HeaderItem {
                    original_mnemonic: mnemonic.clone(),
                    session_mnemonic: mnemonic,
                    unit: String::new(),
                    value: Value::Str(String::new()),
                    descr: format!("Auto-generated from excess data column {}", col_idx),
                    data: Value::Str(String::new()),
                },
                curve_data: columns[col_idx].clone(),
                string_data: None,
            };
            curves_section.items.push(ItemWrapper::Curve(item));
        }
    }
}

fn detect_index_unit(las: &LASFile) -> Option<String> {
    // Get STRT unit
    let strt_unit = las.well_section.find_index_by_mnemonic("STRT")
        .and_then(|idx| {
            let item: &ItemWrapper = &las.well_section.items[idx];
            let unit = item.unit();
            if unit.is_empty() { None } else { normalize_depth_unit(unit) }
        });

    // Get first curve unit
    let curve_unit = las.curves_section.items.first()
        .and_then(|item| {
            let unit = item.unit();
            if unit.is_empty() { None } else { normalize_depth_unit(unit) }
        });

    // If both are present and disagree, return None (inconsistent)
    match (&strt_unit, &curve_unit) {
        (Some(s), Some(c)) if s != c => None,
        (Some(s), _) => Some(s.clone()),
        (_, Some(c)) => Some(c.clone()),
        _ => None,
    }
}

fn normalize_depth_unit(unit: &str) -> Option<String> {
    let upper = unit.to_uppercase().trim().to_string();
    match upper.as_str() {
        "FT" | "F" | "FEET" | "FOOT" => Some("FT".to_string()),
        "M" | "METER" | "METERS" | "METRES" | "METRE" | "\u{043C}" => Some("M".to_string()),
        ".1IN" | "0.1IN" => Some(".1IN".to_string()),
        _ => None, // Unknown unit
    }
}

fn apply_mnemonic_case(las: &mut LASFile, case: &str) {
    let transform = |name: &str| -> String {
        match case {
            "upper" => name.to_uppercase(),
            "lower" => name.to_lowercase(),
            _ => name.to_string(), // "preserve" or unknown
        }
    };

    for section in [
        &mut las.version_section,
        &mut las.well_section,
        &mut las.curves_section,
        &mut las.params_section,
    ] {
        for item in &mut section.items {
            let new_orig = transform(item.original_mnemonic());
            let new_sess = transform(item.session_mnemonic());
            match item {
                ItemWrapper::Header(h) => {
                    h.original_mnemonic = new_orig;
                    h.session_mnemonic = new_sess;
                }
                ItemWrapper::Curve(c) => {
                    c.header.original_mnemonic = new_orig;
                    c.header.session_mnemonic = new_sess;
                }
            }
        }
    }
}

/// Python-facing read function
pub fn py_read(py: Python<'_>, source: &Bound<'_, PyAny>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<LASFile> {
    let ignore_header_errors = kwargs
        .and_then(|kw| kw.get_item("ignore_header_errors").ok().flatten())
        .and_then(|v| v.extract::<bool>().ok())
        .unwrap_or(false);

    let mnemonic_case = kwargs
        .and_then(|kw| kw.get_item("mnemonic_case").ok().flatten())
        .and_then(|v| v.extract::<String>().ok());

    let ignore_data = kwargs
        .and_then(|kw| kw.get_item("ignore_data").ok().flatten())
        .and_then(|v| v.extract::<bool>().ok())
        .unwrap_or(false);

    let null_policy = kwargs
        .and_then(|kw| kw.get_item("null_policy").ok().flatten())
        .map(|v| {
            // Check if it's a pure float list
            if let Ok(values) = v.extract::<Vec<f64>>() {
                return data::NullPolicy::Custom(values);
            }
            // Check if it's a string policy name
            if let Ok(s) = v.extract::<String>() {
                return data::NullPolicy::from_str_or_list(&s);
            }
            // Try as mixed list (strings + numbers)
            if let Ok(seq) = v.iter() {
                let mut floats = Vec::new();
                let mut strings = Vec::new();
                for item in seq {
                    if let Ok(item) = item {
                        if let Ok(f) = item.extract::<f64>() {
                            floats.push(f);
                        } else if let Ok(s) = item.extract::<String>() {
                            strings.push(s);
                        }
                    }
                }
                if !floats.is_empty() || !strings.is_empty() {
                    return data::NullPolicy::CustomMixed { floats, strings };
                }
            }
            data::NullPolicy::Strict
        });

    let read_policy_raw = kwargs
        .and_then(|kw| kw.get_item("read_policy").ok().flatten());
    let read_policy = if let Some(ref rp) = read_policy_raw {
        if let Ok(s) = rp.extract::<String>() {
            Some(s)
        } else {
            // Empty tuple/list = no policies
            None
        }
    } else {
        // Default: apply comma-decimal-mark substitution
        Some("comma-decimal-mark".to_string())
    };

    let ignore_comments = kwargs
        .and_then(|kw| kw.get_item("ignore_comments").ok().flatten())
        .map(|v| {
            // Try Vec<String> first (works for both lists and tuples)
            if let Ok(list) = v.extract::<Vec<String>>() {
                return list;
            }
            if let Ok(s) = v.extract::<String>() {
                return vec![s];
            }
            vec!["#".to_string()]
        })
        .unwrap_or_else(|| vec!["#".to_string()]);

    let index_unit_override = kwargs
        .and_then(|kw| kw.get_item("index_unit").ok().flatten())
        .and_then(|v| v.extract::<String>().ok());

    let (content, detected_encoding) = resolve_source(py, source)?;
    let mut las = read_las(&content, ignore_header_errors, mnemonic_case.as_deref(), ignore_data, null_policy, read_policy, &ignore_comments)?;
    las.encoding = detected_encoding;

    // Apply index_unit override
    if let Some(unit) = index_unit_override {
        las.index_unit = Some(unit);
    }

    Ok(las)
}

fn resolve_source(_py: Python<'_>, source: &Bound<'_, PyAny>) -> PyResult<(String, Option<String>)> {
    // Check if it's a string
    if let Ok(s) = source.extract::<String>() {
        // Multi-line string (LAS content)?
        if s.contains('\n') {
            return Ok((s, None));
        }
        // Single line — treat as filename
        // Check for LiDAR guard
        let path = std::path::Path::new(&s);
        if !path.exists() {
            return Err(PyIOError::new_err(format!("File not found: {}", s)));
        }
        let bytes = std::fs::read(&s)
            .map_err(|e| PyIOError::new_err(format!("Cannot read file: {}: {}", s, e)))?;

        // LiDAR guard: first 4 bytes == "LASF"
        if bytes.len() >= 4 && &bytes[0..4] == b"LASF" {
            return Err(PyIOError::new_err(
                "This is a LiDAR LAS file (binary), not a Log ASCII Standard file"
            ));
        }

        // Try to decode
        return decode_bytes(&bytes);
    }

    // Check for pathlib.Path
    if let Ok(path_str) = source.call_method0("__fspath__") {
        if let Ok(s) = path_str.extract::<String>() {
            let bytes = std::fs::read(&s)
                .map_err(|e| PyIOError::new_err(format!("Cannot read file: {}: {}", s, e)))?;
            return decode_bytes(&bytes);
        }
    }

    // File-like object: call .read()
    if let Ok(content) = source.call_method0("read") {
        if let Ok(s) = content.extract::<String>() {
            return Ok((s, None));
        }
        if let Ok(b) = content.extract::<Vec<u8>>() {
            return decode_bytes(&b);
        }
    }

    Err(PyIOError::new_err("Cannot read from source: expected filename, string, or file-like object"))
}

fn decode_bytes(bytes: &[u8]) -> PyResult<(String, Option<String>)> {
    // BOM detection
    if bytes.starts_with(b"\xEF\xBB\xBF") {
        return Ok((String::from_utf8_lossy(&bytes[3..]).to_string(), Some("utf-8-sig".to_string())));
    }
    if bytes.starts_with(b"\xFF\xFE") {
        let (cow, _, _) = encoding_rs::UTF_16LE.decode(bytes);
        return Ok((cow.to_string(), Some("utf-16-le".to_string())));
    }
    if bytes.starts_with(b"\xFE\xFF") {
        let (cow, _, _) = encoding_rs::UTF_16BE.decode(bytes);
        return Ok((cow.to_string(), Some("utf-16-be".to_string())));
    }

    // Try UTF-8 first
    if let Ok(s) = std::str::from_utf8(bytes) {
        return Ok((s.to_string(), Some("utf-8".to_string())));
    }

    // Fall back to Windows-1252
    let (cow, _, _) = encoding_rs::WINDOWS_1252.decode(bytes);
    Ok((cow.to_string(), Some("windows-1252".to_string())))
}
