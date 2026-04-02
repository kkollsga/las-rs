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
        format!("{}", f)
    } else {
        format!("{}", f)
    }
}

// ---------------------------------------------------------------------------
// HeaderItem
// ---------------------------------------------------------------------------

#[cfg_attr(feature = "python", pyo3::prelude::pyclass(subclass, module = "las_rs._native"))]
#[derive(Debug, Clone)]
pub struct HeaderItem {
    pub original_mnemonic: String,
    pub session_mnemonic: String,
    pub unit: String,
    pub value: Value,
    pub descr: String,
    pub data: Value,
}

// ---------------------------------------------------------------------------
// CurveItem
// ---------------------------------------------------------------------------

#[cfg_attr(feature = "python", pyo3::prelude::pyclass(module = "las_rs._native"))]
#[derive(Debug, Clone)]
pub struct CurveItem {
    pub header: HeaderItem,
    pub curve_data: Vec<f64>,
    pub string_data: Option<Vec<String>>,
    pub dtype_override: Option<String>,
}

// ---------------------------------------------------------------------------
// ItemWrapper -- internal enum to hold either HeaderItem or CurveItem
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

#[cfg_attr(feature = "python", pyo3::prelude::pyclass(module = "las_rs._native"))]
#[derive(Debug, Clone)]
pub struct SectionItems {
    pub items: Vec<ItemWrapper>,
    pub mnemonic_transforms: bool,
}

impl SectionItems {
    pub fn compare_mnemonics(&self, a: &str, b: &str) -> bool {
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
