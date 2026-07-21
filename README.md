# partner_discount_rule

Reglas de descuento por cliente para Odoo. Permite definir descuentos (%) por
**cliente** o **etiqueta de cliente**, aplicables a una **variante de producto**,
un **producto**, una **categoría de producto** (incluye hijas) o **todos los
productos**, con vigencia opcional por fechas.

## Ramas

| Rama   | Versión de Odoo |
|--------|-----------------|
| `18.0` | Odoo 18         |
| `19.0` | Odoo 19         |

## Cómo funciona

Al elegir producto en una línea de presupuesto (estados *borrador* / *enviado*),
el módulo busca las reglas vigentes que apliquen al cliente (directo, por su
contacto comercial padre, o por etiqueta) y al producto, y aplica la más
específica:

1. Variante de producto
2. Producto
3. Categoría de producto (matchea también categorías hijas)
4. Global (todos los productos)

Ante empate de especificidad gana la regla con menor `sequence`, y luego la de
menor `id`. El descuento se escribe en el campo estándar `discount` de la línea,
por lo que conviene tener activada la opción **Descuentos** en Ajustes de Ventas
para verlo en pantalla.

## Convivencia con el descuento de la lista de precios

Cada regla configura cómo combinarse con el descuento que la tarifa ya haya
puesto en la columna Descuento (campo **Con descuento de tarifa**):

| Modo                        | Comportamiento                                      |
|-----------------------------|-----------------------------------------------------|
| Mayor beneficio al cliente  | Aplica el mayor de los dos porcentajes              |
| Acumulado                   | Suma ambos porcentajes (tope 100%)                  |
| Sobreescribir (default)     | La regla pisa el descuento de la tarifa             |

Esto solo aplica sobre la **columna descuento**: si la tarifa está configurada
para incluir el descuento en el precio unitario (precio ya rebajado), la regla
no lo detecta como descuento y el porcentaje se aplica sobre ese precio.

## Condiciones adicionales

Cada regla puede exigir además (0 = sin condición):

- **Cantidad mínima**: la línea debe alcanzar esa cantidad (en la unidad de
  medida de la línea), como la cantidad mínima de las listas de precios.
- **Monto mínimo del pedido**: el total del pedido — sin impuestos y **antes
  de descuentos** (precio × cantidad) — debe alcanzar ese monto, expresado en
  la moneda de la compañía. Se usa el bruto para que el propio descuento no
  desactive la condición. Al agregar o modificar cualquier línea se re-evalúan
  los descuentos de todas las líneas del pedido, así las líneas cargadas antes
  de alcanzar el monto también reciben el descuento.

## Configuración

Menú **Ventas → Configuración → Reglas de descuento** (grupo *Administrador de
ventas*). Cada cliente muestra un botón inteligente con las reglas que le
aplican.

## Instalación

Clonar la rama correspondiente a tu versión de Odoo y agregar la carpeta al
`addons_path`:

```bash
git clone -b 18.0 https://github.com/aceleradora-la/partner_discount_rule.git
```

Dependencias: `sale_management` (estándar).

## Tests

El módulo no incluye tests automáticos: se quitaron para que los builds de
Odoo.sh (que corren toda la suite sobre una copia de producción) no bloqueen
los deploys. La suite original quedó en el historial de git y puede
restaurarse revirtiendo el commit que eliminó `partner_discount_rule/tests/`.
