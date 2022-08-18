from wtforms import DecimalField, StringField, validators

from slamd.materials.processing.forms.materials_form import MaterialsForm


class AggregatesForm(MaterialsForm):
    fine_aggregates = DecimalField(
        label='Fine Aggregates (kg/m³)',
        validators=[
            validators.Optional()
        ]
    )

    coarse_aggregates = DecimalField(
        label='Coarse Aggregates (kg/m³)',
        validators=[
            validators.Optional()
        ]
    )

    fa_density = DecimalField(
        label='FA Density (kg/m³)',
        validators=[
            validators.Optional()
        ])

    ca_density = DecimalField(
        label='CA Density (kg/m³)',
        validators=[
            validators.Optional()
        ])
