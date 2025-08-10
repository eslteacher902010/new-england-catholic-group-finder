from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, PasswordField, SelectField, BooleanField,
    TextAreaField, DateField, TimeField, URLField, DateTimeLocalField, FloatField
)
from wtforms.validators import DataRequired, Email, Optional, Length, URL, NumberRange



def get_approved_groups():
    from main import Catholic  # lazy import to avoid circular issue
    return Catholic.query.filter_by(status="approved").all()





# TODO: Create a RegisterForm to register new users
class RegisterForm(FlaskForm):
    name = StringField("", validators=[DataRequired()])
    email = StringField("", validators=[DataRequired(), Email()])
    password = PasswordField("", validators=[DataRequired()])
    subscribe = BooleanField("Subscribe to updates")
    submit = SubmitField("Sign Me Up!")


# TODO: Create a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class CommentForm(FlaskForm):
    comment_text = TextAreaField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")


class EventForm(FlaskForm):
    title = TextAreaField("Title of Event", validators=[DataRequired()])

    description = StringField("Description", validators=[DataRequired()],
                              render_kw={"placeholder": "One to two sentences about what will happen at this event"})

    date = DateField("Date", validators=[DataRequired()],
                     render_kw={"placeholder": "MM/DD/YYYY", "type": "date"})

    time = TimeField("Time", validators=[DataRequired()],
                     render_kw={"placeholder": "HH:MM", "type": "time"})

    address = StringField("Address", validators=[DataRequired()],
                          render_kw={"placeholder": "e.g., 123 Main St"})

    zip_code = StringField("ZIP Code", validators=[Optional(), Length(max=10)],
                          render_kw={"placeholder": "e.g., 02118"})

    link = StringField("Link to event", validators=[Optional()],
                       render_kw={"placeholder": "If possible, a link to the event"})

    group = SelectField("Group", coerce=int, validators=[Optional()]) # populate choices in your route

    custom_group = StringField("Or Create a New Group", validators=[Optional()],
                               render_kw={"placeholder": "e.g. Catholic Young Adults of Quincy"})

    is_recurring = BooleanField('Is this a recurring event?')
    recurring_week = SelectField(
        'Week of Month',
        choices=[('', 'Select'), ('first', 'First'), ('second', 'Second'), ('third', 'Third'), ('fourth', 'Fourth'),
                 ('last', 'Last')]
    )
    recurring_day = SelectField(
        'Day of the Week',
        choices=[('', 'Select')] + [(day, day) for day in
                                    ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']]
    )
    recurring_time = StringField('Recurring Time (e.g., 6:00 PM)')

    status = SelectField("Status", choices=[("pending", "Pending"),
                                            ("approved", "Approved"),
                                            ("rejected", "Rejected")])



    submit = SubmitField("Submit Event")


class GroupForm(FlaskForm):
    name = StringField("Group Name", validators=[DataRequired()])
    map_url = StringField("Map URL", validators=[DataRequired()])
    img_url = StringField("Image URL", validators=[Optional()], render_kw={"placeholder": "optional"})
    city = StringField("City", validators=[DataRequired()])
    state = StringField("State", validators=[DataRequired()])
    most_current_event = StringField("Current Event", validators=[Optional()],  render_kw={"placeholder": "optional"})
    website_address = StringField("Website", validators=[Optional()], render_kw={"placeholder": "optional"})
    social_media=StringField("social media", validators=[Optional()], render_kw={"placeholder": "optional"})

    approximate_age_range = SelectField("Approximate Age Range", choices=[
        ('', '-- Select Age Range --'),
        ('18–22', '18–22'),
        ('20s', '20s'),
        ('20s–30s', '20s–30s'),
        ('30s', '30s'),
        ('30s–40s', '30s–40s'),
        ('All Ages', 'All Ages'),
        ('Other', 'Other')

    ], validators=[DataRequired()])

    custom_age_range = StringField("Please specify", validators=[Optional()])

    lat = FloatField("Latitude", validators=[Optional(), NumberRange(-90, 90)])
    lon = FloatField("Longitude", validators=[Optional(), NumberRange(-180, 180)])

    # New renamed field
    group_details = TextAreaField("Helpful notes for someone visiting this group")

    contact = StringField("Contact", validators=[Optional()],  render_kw={"placeholder": "optional"})
    submit = SubmitField("Add Group")

class StartGroup(FlaskForm):
    name = StringField("Group Name", validators=[DataRequired()])

    city = StringField("City", validators=[DataRequired()])

    state = StringField("State", validators=[DataRequired()])

    zip_code = StringField("ZIP Code", validators=[Optional(), Length(max=10)])


    approximate_age_range = SelectField("Approximate Age Range", choices=[
        ('', '-- Select Age Range --'),
        ('18–22', '18–22'),
        ('20s', '20s'),
        ('20s–30s', '20s–30s'),
        ('30s', '30s'),
        ('30s–40s', '30s–40s'),
        ('All Ages', 'All Ages'),
        ('Other', 'Other'),

        ], validators = [DataRequired()])

    custom_age_range = StringField("Please specify", )


    group_type = SelectField("Group Type", choices=[
        ('', '-- Select Type --'),
        ('Social', 'Social'),
        ('Prayer', 'Prayer'),
        ('Service', 'Service'),
        ('Study', 'Study'),
        ('Other', 'Other')
    ], validators=[Optional()])

    the_why = TextAreaField("What’s the vision for your group?")

    contact = StringField("Contact", validators=[Optional()],
                          render_kw={"placeholder": "e.g. maria@example.com or @insta_handle"})

    submit = SubmitField("Submit Your Group Idea")


# class GroupForm(FlaskForm):
#     name = StringField("Group Name", validators=[DataRequired()])
#     city = StringField("City", validators=[DataRequired()])
#     state = StringField("State", validators=[DataRequired()])
#     group_details = TextAreaField("Details", validators=[Optional()])
#     img_url = URLField("Image URL", validators=[Optional(), URL()])
#     website_address = URLField("Website", validators=[Optional(), URL()])
#     social_media = URLField("Social Media", validators=[Optional(), URL()])
#     map_url = URLField("Map URL", validators=[Optional(), URL()])
#
#
# class EventForm(FlaskForm):
#     title = StringField("Title", validators=[DataRequired()])
#     description = TextAreaField("Description", validators=[Optional()])
#     date_time = DateTimeLocalField("Date and Time", format="%Y-%m-%dT%H:%M", validators=[Optional()])
#     status = SelectField("Status", choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")])