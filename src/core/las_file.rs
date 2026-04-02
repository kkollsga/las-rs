use std::collections::HashMap;
use crate::core::types::{HeaderItem, ItemWrapper, SectionItems, Value};

#[pyo3::prelude::pyclass(module = "las_rs._native")]
#[derive(Debug, Clone)]
pub struct LASFile {
    pub version_section: SectionItems,
    pub well_section: SectionItems,
    pub curves_section: SectionItems,
    pub params_section: SectionItems,
    pub other_section: String,
    pub custom_sections: HashMap<String, SectionItems>,
    pub encoding: Option<String>,
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
