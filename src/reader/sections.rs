/// Section discovery: scan lines for `~` prefixes and classify them.

#[derive(Debug, Clone)]
pub struct SectionRange {
    pub title: String,
    pub kind: SectionKind,
    pub start_line: usize,  // first content line (after the ~TITLE line)
    pub end_line: usize,    // exclusive
}

#[derive(Debug, Clone, PartialEq)]
pub enum SectionKind {
    Version,
    Well,
    Curves,
    Parameter,
    Other,
    Data,
    Custom(String),
}

pub fn discover_sections(lines: &[&str]) -> Vec<SectionRange> {
    let mut sections = Vec::new();
    let mut i = 0;
    while i < lines.len() {
        let trimmed = lines[i].trim();
        if trimmed.starts_with('~') {
            let title = trimmed[1..].to_string();
            let kind = classify_section(&title);
            let start_line = i + 1;
            // Find end: next ~ line or EOF
            let mut end_line = lines.len();
            for j in start_line..lines.len() {
                let t = lines[j].trim();
                if t.starts_with('~') {
                    end_line = j;
                    break;
                }
            }
            sections.push(SectionRange {
                title,
                kind,
                start_line,
                end_line,
            });
            i = start_line;
        } else {
            i += 1;
        }
    }
    sections
}

fn classify_section(title: &str) -> SectionKind {
    let upper = title.to_uppercase();
    // Get the first "word" (up to first space or end)
    let first_word = upper.split_whitespace().next().unwrap_or("");

    // LAS 3.0 compound section names. The standard primary dataset is titled
    // ~Log_Definition / ~Log_Parameter / ~Log_ASCII; Petrel and LAS-2.0-derived
    // exports name the same primary dataset ~Curve_Definition / ~Curve_Parameter
    // / ~Curve_ASCII. Recognize both the LOG and CURVE prefixes so either
    // spelling parses. Secondary datasets (~Drilling_Definition, ~Tops_Definition,
    // …) intentionally fall through to Custom and are retained as extra sections
    // rather than merged into the primary Curves/Data.
    if upper.contains("LOG_DEFINITION") || upper.contains("LOG DEFINITION")
        || upper.contains("CURVE_DEFINITION") || upper.contains("CURVE DEFINITION") {
        return SectionKind::Curves;
    }
    if upper.contains("LOG_PARAMETER") || upper.contains("LOG PARAMETER")
        || upper.contains("CURVE_PARAMETER") || upper.contains("CURVE PARAMETER") {
        return SectionKind::Parameter;
    }
    if upper.contains("_DATA")
        || upper.starts_with("LOG_ASCII") || upper.starts_with("LOG ASCII")
        || upper.starts_with("CURVE_ASCII") || upper.starts_with("CURVE ASCII") {
        if !upper.starts_with("A") {
            return SectionKind::Data;
        }
    }

    // Standard sections: match by first word or single letter
    match first_word {
        "V" | "VERSION" => SectionKind::Version,
        "W" | "WELL" => SectionKind::Well,
        "C" | "CURVE" | "CURVES" => SectionKind::Curves,
        "P" | "PARAMETER" | "PARAMS" => SectionKind::Parameter,
        "O" | "OTHER" => SectionKind::Other,
        "A" | "ASCII" => SectionKind::Data,
        _ => {
            // Check if first word starts with a standard prefix followed by more text
            // e.g., "VERSION INFORMATION" → first word is "VERSION" (handled above)
            // "ASCII LOG DATA" → first word is "ASCII" (handled above)
            // For anything else, check single-char prefix only if the word IS a single char
            if first_word.len() == 1 {
                match first_word.chars().next().unwrap() {
                    'V' => SectionKind::Version,
                    'W' => SectionKind::Well,
                    'C' => SectionKind::Curves,
                    'P' => SectionKind::Parameter,
                    'O' => SectionKind::Other,
                    'A' => SectionKind::Data,
                    _ => SectionKind::Custom(title.to_string()),
                }
            } else {
                SectionKind::Custom(title.to_string())
            }
        }
    }
}
