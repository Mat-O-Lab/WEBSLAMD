from flask_wtf import FlaskForm as Form
from wtforms import StringField, SelectField, FieldList, FormField, validators, SubmitField

from slamd.materials.forms.add_property_form import AddPropertyForm


class BaseMaterialsForm(Form):

    # TODO: validation -> name must be unique
    material_name = StringField(
        label='Name',
        validators=[validators.DataRequired(
            message="Material name cannot be empty")]
    )

    material_type = SelectField(
        label='Material type',
        validators=[validators.DataRequired()],
        choices=['Powder', 'Liquid', 'Aggregates',
                 'Admixture', 'Additive', 'Process', 'Custom', 'Costs']
    )

    additional_properties = FieldList(FormField(AddPropertyForm),
                                      label='Custom Property',
                                      min_entries=1,
                                      max_entries=10)

    submit = SubmitField('Add material')
