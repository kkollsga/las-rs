use std::fmt;

#[derive(Debug)]
pub enum LasError {
    Header(String),
    Data(String),
    UnknownUnit(String),
    Io(String),
    KeyError(String),
}

impl fmt::Display for LasError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LasError::Header(msg) => write!(f, "LAS header error: {}", msg),
            LasError::Data(msg) => write!(f, "LAS data error: {}", msg),
            LasError::UnknownUnit(msg) => write!(f, "Unknown unit: {}", msg),
            LasError::Io(msg) => write!(f, "I/O error: {}", msg),
            LasError::KeyError(msg) => write!(f, "{}", msg),
        }
    }
}

impl std::error::Error for LasError {}
