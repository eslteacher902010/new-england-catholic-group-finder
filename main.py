import os
import csv
import calendar
from datetime import datetime, timedelta
from typing import Optional



from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, Response, abort, make_response
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user, UserMixin
)
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, Boolean
from dateutil.parser import parse as parse_datetime
from opencage.geocoder import OpenCageGeocode
from functools import wraps
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime

from forms import StartGroup, RegisterForm, LoginForm, EventForm, GroupForm


NEW_ENGLAND_STATES = {"MA", "ME", "NH", "VT", "RI", "CT"}


load_dotenv()
geocoder = OpenCageGeocode(os.getenv("API_KEY"))


# Load environment variables


# Initialize Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev")

# Use /data on Fly (mounted volume), else local file
basedir = os.path.abspath(os.path.dirname(__file__))
data_dir = "/data"

if os.path.isdir(data_dir):
    os.makedirs(data_dir, exist_ok=True)  # safe no-op if it exists
    db_path = os.path.join(data_dir, "db.sqlite")
else:
    db_path = os.path.join(basedir, "local.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # optional tidy




csrf = CSRFProtect(app)


# Set up DB base and SQLAlchemy
class Base(DeclarativeBase): pass
db = SQLAlchemy(model_class=Base)
db.init_app(app)
migrate = Migrate(app, db)


# Set up login manager
login_manager = LoginManager()
login_manager.init_app(app)

# table
signups_table = db.Table(
    "signups",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True)
)


# User model
class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(150), nullable=False)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    signed_up_events = db.relationship(
        "Event",
        secondary=signups_table,
        back_populates="attendees"
    )

    followed_groups = db.relationship(
        'Catholic',
        secondary='followers',
        backref='followers'
    )


@app.get("/healthz")
def healthz():
    return "ok", 200




def import_events_from_csv(file_path):
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date_str = f"{row['date']} {row['time']}"
            event = Event(
                title=row['title'],
                date_time=datetime.strptime(date_str, "%Y-%m-%d %H:%M"),
                address=row.get('address'),
                zip_code=row.get('zip_code'),
                description=row.get('description'),
                group_id=int(row.get('group_id')),
                link=row.get('link') or None,
                user_id=int(row.get('user_id'))  # ⚠️ Make sure this user exists!
            )
            db.session.add(event)
        db.session.commit()
        print("✅ Events imported successfully!")




@app.route("/group/<int:group_id>")
def group_detail(group_id):
    group = db.get_or_404(Catholic, group_id)
    return render_template("group_detail.html", group=group)



def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated



@app.route("/admin/edit/group/<int:group_id>", methods=["GET", "POST"])
@login_required
def edit_group(group_id):

    if not current_user.is_admin:
        abort(403)

    group = Catholic.query.get_or_404(group_id)
    form = GroupForm(request.form, obj=group)  # Pre-fill form with group data
    print("Form valid:", form.validate_on_submit())
    print("Form errors:", form.errors)

    if form.validate_on_submit():
        # Handle special "Other" case for age range
        if form.approximate_age_range.data == "Other" and form.custom_age_range.data:
            group.approximate_age_range = form.custom_age_range.data
        else:
            group.approximate_age_range = form.approximate_age_range.data

        form.populate_obj(group)  # Populate remaining fields
        db.session.commit()
        flash("Group updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/edit_group.html", form=form)



@app.route("/admin/edit/event/<int:event_id>", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    if not current_user.is_admin:
        abort(403)

    event = Event.query.get_or_404(event_id)
    form = EventForm(request.form,obj=event)

    if form.validate_on_submit():
        form.populate_obj(event)
        db.session.commit()
        flash("Event updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/edit_event.html", form=form)




@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# Catholic Group model
class Catholic(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    city: Mapped[str] = mapped_column(String(250), nullable=True)
    state: Mapped[str] = mapped_column(String(250), nullable=True)
    group_details: Mapped[str] = mapped_column(String(500), nullable=True)
    website_address: Mapped[str] = mapped_column(String(250), nullable=True)
    social_media: Mapped[str] = mapped_column(String(250), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=True)
    lon: Mapped[float] = mapped_column(Float, nullable=True)
    img_url: Mapped[str] = mapped_column(String(500), nullable=True)
    approximate_age_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    map_url: Mapped[str] = mapped_column(String(500), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(db.String(10), nullable=False)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    events = db.relationship("Event", back_populates="group", cascade="all, delete")


    # ✅ Store the approval status in the DB
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    user = db.relationship("User", backref="groups")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "group_details": self.group_details,
            "website_address": self.website_address,
            "social_media": self.social_media,
            "lat": self.lat,
            "lon": self.lon,
            "img_url": self.img_url,
            "map_url": self.map_url,
            "status": self.status,
            "zip_code":self.zip_code,
            "subscribed": self.subscribed


        }



class Event(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    date_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    address: Mapped[Optional[str]] = mapped_column(String(250))
    zip_code: Mapped[Optional[str]] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="pending")

    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_day: Mapped[Optional[str]] = mapped_column(String(20))
    recurring_week: Mapped[Optional[str]] = mapped_column(String(20))
    recurring_time: Mapped[Optional[str]] = mapped_column(String(20))

    group_id: Mapped[int] = mapped_column(ForeignKey("catholic.id"), index=True)
    group: Mapped["Catholic"] = db.relationship("Catholic", back_populates="events")
    link = db.Column(db.String(300), nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)

    attendees = db.relationship(
        "User",
        secondary=signups_table,
        back_populates="signed_up_events",
    )



    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "date_time": self.date_time.isoformat() if self.date_time else None,
            "address": self.address,  # now this won't crash
            "zip_code": self.zip_code,
            "status": self.status,
            "city": self.group.city if self.group else None,
            "ics_url": url_for("download_ical", event_id=self.id),
            "is_internal": True,
            "is_recurring": self.is_recurring,
            "recurring_day": self.recurring_day,
            "recurring_week": self.recurring_week,
            "recurring_time": self.recurring_time,
            "link": self.link
        }


followers = db.Table('followers',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('catholic.id'))
)




# ---------- ROUTES ----------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/all")
def get_all_groups():
    result = db.session.execute(
        db.select(Catholic).where(Catholic.status == "approved")
    )
    approved_groups = result.scalars().all()
    return jsonify(groups=[group.to_dict() for group in approved_groups])

@app.route("/data/events.json")
def get_events_json():
    events = Event.query.order_by(Event.date_time).all()
    return jsonify([e.to_dict() for e in events])

@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")


@app.route("/data/groups.json")
def groups_json():
    groups = Catholic.query.all()
    return jsonify([
        {
            "name": g.name,
            "description": g.group_details,
            "lat": g.lat,
            "lon": g.lon,
            "city": g.city,
            "state": g.state,
            "website": g.website_address,
            "social": g.social_media
        }
        for g in groups if g.lat and g.lon  # only return geocoded groups
    ])


@login_manager.unauthorized_handler
def unauthorized():
    flash("Please log in first.", "warning")
    return redirect(url_for("login"))


@app.route("/submit-event", methods=["POST"])
@login_required
def submit_event():
    form = EventForm()

    if form.validate_on_submit():
        selected_group_id = form.group.data  # This is now an int (or -1)
        custom_group_name = form.custom_group.data.strip() if form.custom_group.data else None

        group_id = None

        if selected_group_id == -1 and custom_group_name:
            # User selected "Other" and provided a custom name
            existing_group = Catholic.query.filter_by(name=custom_group_name).first()
            if existing_group:
                group_id = existing_group.id
            else:
                new_group = Catholic(name=custom_group_name, status="pending")
                db.session.add(new_group)
                db.session.flush()  # to get new_group.id before commit
                group_id = new_group.id

        elif selected_group_id != -1:
            group_id = selected_group_id  # user picked from dropdown

        # Now build the event
        if form.is_recurring.data:
            new_event = Event(
                title=form.title.data,
                description=form.description.data,
                is_recurring=True,
                recurring_day=form.recurring_day.data,
                recurring_week=form.recurring_week.data,
                recurring_time=form.recurring_time.data,
                group_id=group_id,
                link=form.link.data,
                address=form.address.data,
                zip_code=form.zip_code.data,
                user_id=current_user.id,
                status="pending"
            )
        else:
            new_event = Event(
                title=form.title.data,
                description=form.description.data,
                date_time=datetime.combine(form.date.data, form.time.data),
                is_recurring=False,
                group_id=group_id,
                link=form.link.data,
                address=form.address.data,
                zip_code=form.zip_code.data,
                user_id=current_user.id,
                status="pending"
            )

        db.session.add(new_event)
        db.session.commit()
        return jsonify(success=True)

    return jsonify(success=False)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))  # Or redirect to "home" if you prefer



@app.route("/search_zip")
def search_zip():
    zip_code = request.args.get("zip")

    if not zip_code:
        # Render a page that shows just the form, nothing filtered yet
        return render_template("search_results.html", zip_code=None, groups=[])

    # Search for groups by zip
    groups = db.session.execute(
        db.select(Catholic).where(Catholic.zip_code == zip_code)
    ).scalars().all()

    return render_template("search_results.html", zip_code=zip_code, groups=groups)



@app.route("/region/<slug>")
def region_view(slug):
    region_states = {
        "greater-boston": ["MA"],
        "western-ma": ["MA"],
        "new-hampshire": ["NH"],
        "vermont": ["VT"],
        "rhode-island": ["RI"],
        "connecticut": ["CT"],
        "maine": ["ME"]
    }
    states = region_states.get(slug, [])
    groups = Catholic.query.filter(Catholic.state.in_(states)).all()
    return render_template("region.html", slug=slug.replace("-", " ").title(), groups=groups)


@app.route("/calendar", methods=["GET", "POST"])
def calendar_view():
    form = EventForm()
    form.group.choices = [(g.id, g.name) for g in Catholic.query.all()]
    form.group.choices.append((-1, "Other"))  # Special value for custom input

    now = datetime.now()
    year = now.year
    month = now.month
    month_name = now.strftime("%B")
    first_weekday, num_days = calendar.monthrange(year, month)

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        month_name=month_name,
        first_weekday=first_weekday,
        num_days=num_days,
        form=form
    )



@app.route("/data/groups.csv")
def groups_csv():
    groups = Catholic.query.all()
    def generate():
        fieldnames = ["id", "name", "city", "state", "website_address", "lat", "lon"]
        yield ",".join(fieldnames) + "\n"
        for g in groups:
            row = {f: getattr(g, f, "") or "" for f in fieldnames}
            yield ",".join(str(row[f]) for f in fieldnames) + "\n"
    return Response(generate(), mimetype='text/csv')

from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("✅ Logged in successfully.", "success")
            return redirect(url_for("home"))
        else:
            flash("❌ Invalid credentials", "danger")

    return render_template("login.html", form=form)


from werkzeug.security import generate_password_hash

@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    form = RegisterForm()

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("⚠️ An account with that email already exists. Please log in or use a different email.", "warning")
            return redirect(url_for("sign_up"))

        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            email=form.email.data,
            password=hashed_password,
            subscribed=form.subscribe.data
        )
        db.session.add(new_user)
        db.session.commit()
        flash("✅ Account created successfully!", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)

@app.route("/add_group", methods=["GET", "POST"])
@login_required
def add_group():
    form = GroupForm()

    if form.validate_on_submit():
        new_group = Catholic()

        if form.approximate_age_range.data == "Other" and form.custom_age_range.data:
            new_group.approximate_age_range = form.custom_age_range.data
        else:
            new_group.approximate_age_range = form.approximate_age_range.data

        form.populate_obj(new_group)  # Fills all other fields
        db.session.add(new_group)
        db.session.commit()
        flash("Group added successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_group.html", form=form)



@app.route("/submit-group", methods=["POST"])
@login_required
@csrf.exempt
def submit_group():
    form = GroupForm()

    if form.validate_on_submit():
        # ✅ Check required fields before geocoding
        if not form.city.data or not form.state.data:
            flash("City and State are required to geocode the group.", "danger")
            return redirect(url_for("add_group"))

        full_location = f"{form.city.data}, {form.state.data}"

        # ✅ Geocode location
        geo_result = geocoder.geocode(full_location)
        lat = lon = None
        state_code = form.state.data  # fallback if geocoder fails

        if geo_result:
            lat = geo_result[0]['geometry']['lat']
            lon = geo_result[0]['geometry']['lng']
            components = geo_result[0]['components']
            state_code = components.get("state_code", form.state.data)
        else:
            flash("⚠️ Could not geocode the location. We'll still review it manually.", "warning")

        # ✅ Only allow groups in New England
        if state_code not in NEW_ENGLAND_STATES:
            flash("❌ Sorry, we are only accepting groups from New England (MA, ME, NH, VT, RI, CT).", "danger")
            return redirect(url_for("groups"))

        # ✅ Create and save group
        new_group = Catholic(
            name=form.name.data,
            city=form.city.data,
            state=state_code,
            zip_code=form.zip_code.data,
            website_address=form.website_address.data,
            social_media=form.social_media.data,
            map_url=form.map_url.data,
            img_url=form.img_url.data,
            group_details=form.group_details.data,
            lat=lat,
            lon=lon,
            user_id=current_user.id,
            status="pending"
        )

        db.session.add(new_group)
        db.session.commit()
        flash("✅ Group submitted successfully.")
        return redirect(url_for("groups"))

    # ❌ Form didn't validate — log errors for debugging
    print("Form validation errors:", form.errors)
    flash("There was a problem submitting your group. Please check the fields and try again.", "danger")
    return render_template("add_group.html", form=form)



@app.route("/preview-group/<int:group_id>")
@login_required
def preview_group(group_id):
    group = db.get_or_404(Catholic, group_id)

    # Optional: Only allow the user who created it, or an admin, to view it
    if group.user_id != current_user.id and not current_user.is_admin:
          abort(403)

    return render_template("preview_group.html", group=group)



@app.route("/start-group", methods=["GET", "POST"])
@login_required
def start_group():
    form = StartGroup()
    if form.validate_on_submit():
        full_location = f"{form.city.data}, {form.state.data} {form.zip_code.data or ''}"
        geo_result = geocoder.geocode(full_location)
        lat = lon = None
        state = None
        zip_code = form.zip_code.data or None

        if form.approximate_age_range.data == "Other" and form.custom_age_range.data:
            age_range = form.custom_age_range.data
        else:
            age_range = form.approximate_age_range.data

        if geo_result:
            lat = geo_result[0]['geometry']['lat']
            lon = geo_result[0]['geometry']['lng']
            components = geo_result[0]['components']
            state = components.get("state_code")
            zip_code = components.get("postcode", zip_code)

            if state not in NEW_ENGLAND_STATES:
                flash("❌ Sorry, we are currently only accepting groups based in New England (MA, ME, NH, VT, RI, CT).", "danger")
                return redirect(url_for("start_group"))
        else:
            flash("Could not find location on map. We’ll still review it manually.", "warning")

        new_group = Catholic(
            name=form.name.data,
            city=form.city.data,
            state=state,
            zip_code=zip_code,
            lat=lat,
            lon=lon,
            user_id=current_user.id,
            status="pending",
            approximate_age_range=age_range  # ✅ This is what was missing
        )
        db.session.add(new_group)
        db.session.commit()
        return redirect(url_for("preview_group", group_id=new_group.id))

    return render_template("start_group.html", form=form)




@app.route("/map")
def map_view():
    return render_template("map.html")


@app.route("/admin/suggested-groups")
@login_required
def suggested_groups():
    if not current_user.is_admin:
        abort(403)  # Optional access control

    groups = db.session.execute(
        db.select(Catholic).where(Catholic.status == "pending")
    ).scalars().all()

    return render_template("suggested_groups.html", groups=groups)


@app.route("/admin/approve/<int:group_id>", methods=["POST"])
@login_required
def approve_group(group_id):
    if not current_user.is_admin:
        abort(403)
    group = db.get_or_404(Catholic, group_id)
    group.status = "approved"
    db.session.commit()
    flash(f"✅ Approved group: {group.name}", "success")
    return redirect(url_for("map_view"))


@app.route("/admin/reject/<int:group_id>", methods=["POST"])
@login_required
def reject_group(group_id):
    if not current_user.is_admin:
        abort(403)

    group = db.get_or_404(Catholic, group_id)
    reason = request.form.get("reason", "").strip()  # ✅ Fix: define first
    group.rejection_reason = reason
    group.status = "rejected"
    db.session.commit()
    flash(f"❌ Rejected group: {group.name}. {('Reason: ' + reason) if reason else ''}", "warning")
    return redirect(url_for("suggested_groups"))




@app.route("/groups")
def show_groups():
    groups = db.session.execute(
        db.select(Catholic).where(Catholic.status == "approved")
    ).scalars().all()
    for group in groups:
        print(group.name, group.map_url)

    return render_template("groups.html", groups=groups)


@app.route("/event/<int:event_id>/calendar.ics")
def download_ical(event_id):
    event = db.get_or_404(Event, event_id)

    uid_base = f"{event.id}@catholicgroups.org"
    entries = []

    if event.is_recurring:
        # --- recurrence logic ---
        weekdays = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        week_offsets = {
            'first': 0, 'second': 1, 'third': 2, 'fourth': 3, 'last': -1
        }

        weekday = weekdays.get(event.recurring_day)
        offset = week_offsets.get(event.recurring_week)
        time_obj = datetime.strptime(event.recurring_time, "%I:%M %p").time()

        for month_offset in range(3):  # generate next 3 monthly occurrences
            today = datetime.today()
            year = today.year + (today.month + month_offset - 1) // 12
            month = (today.month + month_offset - 1) % 12 + 1

            cal = calendar.Calendar().monthdatescalendar(year, month)
            weekday_dates = [week[weekday] for week in cal if week[weekday].month == month]

            if not weekday_dates:
                continue

            if offset == -1:
                event_date = weekday_dates[-1]
            elif offset < len(weekday_dates):
                event_date = weekday_dates[offset]
            else:
                continue

            start = datetime.combine(event_date, time_obj)
            end = start + timedelta(hours=2)

            entries.append(f"""BEGIN:VEVENT
UID:{event.id}-{month_offset}@catholicgroups.org
DTSTAMP:{start.strftime('%Y%m%dT%H%M%S')}
DTSTART:{start.strftime('%Y%m%dT%H%M%S')}
DTEND:{end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{event.title}
DESCRIPTION:{event.description or ''}
LOCATION:{event.address or ''}
END:VEVENT
""")

    else:
        # --- one-time event logic ---
        start = event.date_time.strftime("%Y%m%dT%H%M%S")
        end = (event.date_time + timedelta(hours=2)).strftime("%Y%m%dT%H%M%S")

        entries.append(f"""BEGIN:VEVENT
UID:{uid_base}
DTSTAMP:{start}
DTSTART:{start}
DTEND:{end}
SUMMARY:{event.title}
DESCRIPTION:{event.description or ''}
LOCATION:{event.address or ''}
END:VEVENT
""")

    ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Catholic Groups//Event Calendar//EN
{''.join(entries)}END:VCALENDAR
"""

    response = make_response(ical)
    response.headers["Content-Disposition"] = f"attachment; filename={event.title}.ics"
    response.headers["Content-Type"] = "text/calendar"
    return response

def generate_recurring_dates(start_month, year, recurring_week, recurring_day):
    weekdays = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    week_offsets = {
        'first': 0, 'second': 1, 'third': 2, 'fourth': 3, 'last': -1
    }

    weekday = weekdays[recurring_day]
    offset = week_offsets[recurring_week]

    dates = []

    for month_offset in range(3):  # next 3 months
        month = (start_month + month_offset - 1) % 12 + 1
        year_offset = (start_month + month_offset - 1) // 12
        current_year = year + year_offset

        # Find all days in the month that match the weekday
        month_calendar = calendar.Calendar().monthdatescalendar(current_year, month)
        weekday_dates = [week[weekday] for week in month_calendar if week[weekday].month == month]

        if offset == -1:
            event_date = weekday_dates[-1]
        else:
            if offset < len(weekday_dates):
                event_date = weekday_dates[offset]
            else:
                continue  # Skip if not enough weeks in month

        dates.append(event_date)

    return dates


@app.route("/admin/suggested-events")
@login_required
def suggested_events():
    if not current_user.is_admin:
        abort(403)
    events = db.session.execute(
        db.select(Event).where(Event.status == "pending")
    ).scalars().all()
    return render_template("suggested_events.html", events=events)

@app.route("/admin/approve-event/<int:event_id>", methods=["POST"])
@login_required
def approve_event(event_id):
    if not current_user.is_admin:
        abort(403)
    event = db.get_or_404(Event, event_id)
    event.status = "approved"
    db.session.commit()
    return redirect(url_for("calendar_view"))

@app.route("/admin/reject-event/<int:event_id>", methods=["POST"])
@login_required
def reject_event(event_id):
    if not current_user.is_admin:
        abort(403)
    event = db.get_or_404(Event, event_id)
    event.status = "rejected"
    event.rejection_reason = request.form.get("reason", "")
    db.session.commit()
    return redirect(url_for("suggested_events"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)

    pending_groups = db.session.execute(
        db.select(Catholic).where(Catholic.status == "pending")
    ).scalars().all()

    pending_events = db.session.execute(
        db.select(Event).where(Event.status == "pending")
    ).scalars().all()

    # ✅ Sort events by date_time
    sorted_events = sorted(pending_events, key=lambda e: e.date_time)

    return render_template("admin_dashboard.html", groups=pending_groups, events=sorted_events)



@app.route("/delete-group/<int:group_id>", methods=["POST"])
@login_required
def delete_group(group_id):
    if not current_user.is_admin:
        abort(403)

    group = db.get_or_404(Catholic, group_id)
    db.session.delete(group)
    db.session.commit()
    flash("Group deleted successfully.", "danger")
    return redirect(url_for("admin_dashboard"))



@app.route("/delete-event/<int:event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route('/follow_group/<int:group_id>', methods=['POST'])
@login_required
def follow_group(group_id):
    group = Catholic.query.get_or_404(group_id)
    if group not in current_user.followed_groups:
        current_user.followed_groups.append(group)
        db.session.commit()
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/signup_event/<int:event_id>', methods=['POST'])
@login_required
def signup_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event not in current_user.signed_up_events:
        current_user.signed_up_events.append(event)
        db.session.commit()
    return redirect(url_for('event_detail', event_id=event_id))

@app.route("/event/<int:event_id>")
def event_detail(event_id):
    event = db.get_or_404(Event, event_id)
    return render_template("event_detail.html", event=event)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        # Optional: store/send the message
        print(f"New contact message:\nFrom: {name} <{email}>\nMessage: {message}")

        flash("Thanks for your message! I'll get back to you soon.")
        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/fix-imgs")
def fix_imgs():
    if not current_user.is_authenticated or not current_user.is_admin:
        return "Not authorized", 403

    updates = {
        "Roman Catholic Diocese of Burlington": "https://your-url.jpg",
        "St. Leonard's": "https://another-url.jpg",
    }

    for name, url in updates.items():
        g = Catholic.query.filter_by(name=name).first()
        if g:
            g.img_url = url

    db.session.commit()
    return "Images updated!"


# ---------- RUN ----------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        from werkzeug.security import generate_password_hash

        # Load admin credentials from environment
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "adminpass")

        # Create default admin user if not exists
        default_user = User.query.filter_by(email=admin_email).first()
        if not default_user:
            hashed_password = generate_password_hash(admin_password)
            default_user = User(email=admin_email, password=hashed_password, is_admin=True)
            db.session.add(default_user)
            db.session.commit()

        # Create a default group if none exists
        if not Catholic.query.first():
            new_group = Catholic(
                name="St Clement's Group",
                city="Boston",
                state="MA",
                zip_code="02108",
                website_address="http://www.stclementyoungadults.org/",
                lat=42.347,
                lon=-71.083,
                img_url="https://images.squarespace-cdn.com/.../yac.jpg",
                map_url="https://g.co/kgs/T34keHz",
                user_id=default_user.id
            )
            db.session.add(new_group)
            db.session.commit()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=os.getenv("FLASK_ENV") != "production")
