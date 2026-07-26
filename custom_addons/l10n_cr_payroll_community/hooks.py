import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

_CATEGORY_CODES = {
    "PRUEBAS CR Basic": "CRBASIC",
    "PRUEBAS CR Basic CCSS": "CRBASICCCSS",
    "PRUEBAS CR Pre Tax Allowances": "CRPREALW",
    "PRUEBAS CR Pre Tax Allowances CCSS": "CRPREALWCCSS",
    "PRUEBAS CR Ordinary Salary": "CRSALORD",
    "PRUEBAS CR Ordinary Salary CCSS": "CRSALORDCCSS",
    "PRUEBAS CR Gross": "CRGROSS",
    "PRUEBAS CR Gross CCSS": "CRGROSSCCSS",
    "PRUEBAS CR Ajustes Post Cargas": "CRPOSDED",
    "PRUEBAS CR Ajustes Post Cargas CCSS": "CRDEDEDCCSS",
    "PRUEBAS CR IR TAX": "CRIRTAX",
    "PRUEBAS CR Net": "CRNET",
    "PRUEBAS CR COMP CONTRIB": "CRCOMP",
    "PRUEBAS Prestacion": "CRPRESTACION",
}

_EXTRA_CATEGORIES = {
    "CRPOSDEDCCSS": "CR Asignaciones posteriores a CCSS",
}

_CONDITIONS = {
    "Always True": "none",
    "Python Expression": "python",
}

_AMOUNT_TYPES = {
    "Python Code": "code",
    "Fixed Amount": "fix",
    "Percentage (%)": "percentage",
}

_INPUT_NAMES = {
    "CRFERIADO": "Feriado / día adicional",
    "CRVACACIONES": "Vacaciones",
    "CRPERMENFERMEDAD": "Permiso por enfermedad",
    "CRINCAPEXT": "Incapacidad extendida",
    "CRPERMMAT": "Maternidad",
    "CRINCAPINS": "Incapacidad INS",
    "CRINCAPCCSS": "Incapacidad CCSS",
    "CRHORAEXTRA": "Horas extra",
    "CRHORADOBLE": "Horas extra dobles",
    "CRPERMNOGOCE": "Permiso sin goce",
    "HORAS_FALTA": "Horas no trabajadas",
    "PAGEXT": "Pago extra / retroactivo",
    "DIAS_TRAB": "Días trabajados",
    "CREMBARGOS": "Embargos",
    "CRPENSION": "Pensión",
    "CROTRASDED": "Otras deudas",
    "CRREBAHERRAM": "Rebajos",
    "LO": "Préstamos",
    "SAR": "Adelanto salarial",
    "CRINCAPACUM": "Días de incapacidad acumulados",
    "CRAGUICCSS": "Aguinaldo CCSS",
    "CRDEPENAGUI": "Pensión alimenticia sobre aguinaldo",
    "CRAGUIBONIF": "Aguinaldo sobre bonificación",
}


def _column(reference):
    return re.sub(r"\d", "", reference)


def _read_export(path):
    with zipfile.ZipFile(path) as workbook:
        shared = []
        shared_root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
        for item in shared_root.findall("x:si", _NS):
            shared.append("".join(node.text or "" for node in item.findall(".//x:t", _NS)))

        sheet = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows = []
        for xml_row in sheet.findall(".//x:sheetData/x:row", _NS):
            values = {}
            for cell in xml_row.findall("x:c", _NS):
                value_node = cell.find("x:v", _NS)
                value = value_node.text if value_node is not None else ""
                if cell.get("t") == "s" and value:
                    value = shared[int(value)]
                values[_column(cell.get("r"))] = value
            rows.append(values)

    headers = rows.pop(0)
    by_column = {column: label for column, label in headers.items()}
    return [
        {by_column[column]: value for column, value in row.items() if column in by_column}
        for row in rows
    ]


def _adapt_python(code, rule_code):
    code = code or "result = 0.0"
    if rule_code == "NET_CCSS":
        return """# Las categorías de deducción ya contienen importes negativos.
result = (
    (categories.CRGROSSCCSS or 0.0)
    + (categories.CRPOSDEDCCSS or 0.0)
    + (categories.CRDEDEDCCSS or 0.0)
    + (categories.CRIRTAX or 0.0)
    + (categories.CRPOSDED or 0.0)
    + (categories.CRPRESTACION or 0.0)
)"""
    replacements = {
        "payslip.date_from": "date_from",
        "payslip.date_to": "date_to",
        "inputs.Pension": "inputs.CRPENSION",
        "inputs.CRDEUDA": "inputs.CROTRASDED",
        "categories.CRPERMNOGOCE": "CRPERMNOGOCE",
        "categories.CRFERIADO": "CRFERIADO",
        "categories.CR_IR_TAX": "categories.CRIRTAX",
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    if rule_code == "CRDEDCCSS":
        code = code.replace("rate = 0.1067", "rate = 0.0967")
        code = code.replace("rate = 0.1083", "rate = 0.0983")
    return code


def _condition_type(row):
    """Input-driven rules can safely compute zero without a Python condition."""
    if row["Salary Rule Code"] in {"RENQ1", "RENQ2"}:
        return "python"
    return "none"


def _get_or_create_category(env, company, name):
    code = _CATEGORY_CODES[name]
    category = env["hr.salary.rule.category"].search(
        [("code", "=", code), ("company_id", "=", company.id)], limit=1
    )
    if not category:
        category = env["hr.salary.rule.category"].create(
            {"name": name.replace("PRUEBAS ", ""), "code": code, "company_id": company.id}
        )
    return category


def sync_salary_rules(env):
    source = Path(__file__).parent / "data" / "salary_rules_odoo17.xlsx"
    rows = _read_export(source)
    company = env.company
    categories = {
        name: _get_or_create_category(env, company, name)
        for name in _CATEGORY_CODES
    }
    for code, name in _EXTRA_CATEGORIES.items():
        category = env["hr.salary.rule.category"].search(
            [("code", "=", code), ("company_id", "=", company.id)], limit=1
        )
        if not category:
            env["hr.salary.rule.category"].create(
                {"name": name, "code": code, "company_id": company.id}
            )

    rules = env["hr.salary.rule"]
    created_rules = {}
    for row in rows:
        code = row["Salary Rule Code"].strip()
        values = {
            "name": row["Salary Rule Name"],
            "code": code,
            "category_id": categories[row["Category"]].id,
            "sequence": int(float(row.get("Sequence") or 5)),
            "appears_on_payslip": row.get("Appears on Payslip") == "1",
            "condition_select": _condition_type(row),
            "condition_python": _adapt_python(row.get("Python Condition"), code),
            "amount_select": _AMOUNT_TYPES.get(row.get("Amount Type"), "code"),
            "amount_python_compute": _adapt_python(row.get("Python Code"), code),
            "company_id": company.id,
        }
        rule = rules.search(
            [("code", "=", code), ("company_id", "=", company.id)], limit=1
        )
        if rule:
            rule.write(values)
        else:
            rule = rules.create(values)
        created_rules[code] = rule

    input_owner = {}
    for row in rows:
        rule = created_rules[row["Salary Rule Code"].strip()]
        source_code = "%s\n%s" % (
            row.get("Python Condition", ""),
            row.get("Python Code", ""),
        )
        referenced = set(re.findall(r"\binputs\.([A-Za-z_][A-Za-z0-9_]*)", source_code))
        explicit = (row.get("Inputs/Code") or "").strip()
        if explicit:
            referenced.add(explicit)
        for input_code in sorted(referenced):
            input_code = {"Pension": "CRPENSION", "CRDEUDA": "CROTRASDED"}.get(
                input_code, input_code
            )
            input_owner.setdefault(input_code, rule)

    rule_inputs = env["hr.rule.input"]
    migrated_rules = rules.browse([rule.id for rule in created_rules.values()])
    for input_code, rule in input_owner.items():
        existing = rule_inputs.search(
            [("code", "=", input_code), ("input_id", "in", migrated_rules.ids)],
            limit=1,
        )
        if not existing:
            rule_inputs.create(
                {
                    "name": _INPUT_NAMES.get(input_code, input_code.replace("_", " ").title()),
                    "code": input_code,
                    "input_id": rule.id,
                }
            )

    structure = env["hr.payroll.structure"].search(
        [("code", "=", "CR_QUINCENAL"), ("company_id", "=", company.id)], limit=1
    )
    structure_values = {
        "name": "Costa Rica - Nómina quincenal",
        "code": "CR_QUINCENAL",
        "company_id": company.id,
        "rule_ids": [(6, 0, migrated_rules.ids)],
    }
    if structure:
        structure.write(structure_values)
    else:
        env["hr.payroll.structure"].create(structure_values)


def post_init_hook(env):
    sync_salary_rules(env)
