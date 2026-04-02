use pyo3::prelude::*;
use pyo3::create_exception;

create_exception!(las_rs, LASDataError, pyo3::exceptions::PyException);
create_exception!(las_rs, LASHeaderError, pyo3::exceptions::PyException);
create_exception!(las_rs, LASUnknownUnitError, pyo3::exceptions::PyException);
