use pyo3::prelude::*;
use pyo3::types::PyDict;
use crate::types::{HeaderItem, CurveItem, SectionItems};
use crate::las_file::LASFile;
use crate::errors::{LASDataError, LASHeaderError, LASUnknownUnitError};
use crate::reader::header;

#[pyfunction]
#[pyo3(signature = (source, **kwargs))]
fn read(py: Python<'_>, source: &Bound<'_, PyAny>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<LASFile> {
    crate::las_file::py_read(py, source, kwargs)
}

#[pyfunction]
fn read_header_line(py: Python<'_>, line: &str) -> PyResult<Option<PyObject>> {
    match header::parse_header_line(line) {
        Some(parsed) => {
            let dict = PyDict::new(py);
            dict.set_item("name", &parsed.mnemonic)?;
            dict.set_item("unit", &parsed.unit)?;
            dict.set_item("value", &parsed.value)?;
            dict.set_item("descr", &parsed.descr)?;
            Ok(Some(dict.into_any().unbind()))
        }
        None => Ok(None),
    }
}

/// Reader submodule exposed to Python
#[pymodule]
fn reader(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(read_header_line, m)?)?;
    Ok(())
}

#[pymodule]
pub fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<HeaderItem>()?;
    m.add_class::<CurveItem>()?;
    m.add_class::<SectionItems>()?;
    m.add_class::<LASFile>()?;
    m.add_function(wrap_pyfunction!(read, m)?)?;
    m.add("LASDataError", m.py().get_type::<LASDataError>())?;
    m.add("LASHeaderError", m.py().get_type::<LASHeaderError>())?;
    m.add("LASUnknownUnitError", m.py().get_type::<LASUnknownUnitError>())?;

    // Add reader submodule
    let reader_mod = PyModule::new(m.py(), "reader")?;
    reader(&reader_mod)?;
    m.add_submodule(&reader_mod)?;

    Ok(())
}
