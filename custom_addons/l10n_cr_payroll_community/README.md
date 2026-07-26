# Nómina de Costa Rica para OpenHRMS Community

Este módulo migra el archivo `salary_rules_odoo17.xlsx` a Odoo 19 cuando se
instala. Crea o actualiza:

- 39 reglas salariales;
- 15 categorías;
- los inputs detectados en las condiciones y cálculos;
- la estructura `Costa Rica - Nómina quincenal` (`CR_QUINCENAL`).

## Supuestos

- La nómina se procesa por quincenas.
- El salario de `hr.version.wage` es mensual.
- Los importes de deducciones son negativos.
- Para 2026 se usa 9,83 % como cuota obrera y 26,83 % como cuota patronal.
- Los tramos mensuales de renta son 918.000, 1.347.000, 2.364.000 y
  4.727.000 colones.

## Configuración posterior

1. Asignar `Costa Rica - Nómina quincenal` en la versión contractual activa
   de cada empleado.
2. Configurar salario mensual y horario laboral.
3. Crear una nómina de prueba del día 1 al 15.
4. Completar únicamente los inputs que correspondan; los demás deben quedar
   en cero.
5. Comparar bruto, CCSS, renta y neto con un cálculo aprobado por contabilidad.
6. Repetir la prueba para la segunda quincena y para casos de incapacidad,
   horas extra, vacaciones y deducciones.

No se debe utilizar en producción hasta completar y documentar esas pruebas.
