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
from werkzeug.security import check_password_hash

from forms import StartGroup, RegisterForm, EventForm, GroupForm, LoginForm


NEW_ENGLAND_STATES = {"MA", "ME", "NH", "VT", "RI", "CT"}


load_dotenv()
geocoder = OpenCageGeocode(os.getenv("API_KEY"))


# Load environment variables


# Initialize Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///catholic_groups.db'
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev")

csrf = CSRFProtect(app)

# Set up DB base and SQLAlchemy
class Base(DeclarativeBase): pass
db = SQLAlchemy(model_class=Base)
db.init_app(app)
migrate = Migrate(app, db)




# Set up login manager
login_manager = LoginManager()
login_manager.init_app(app)

# User model
class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(150), nullable=False)
    subscribed = db.Column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


    followed_groups = db.relationship(
        'Catholic',
        secondary='followers',
        backref='followers'
    )

    signed_up_events = db.relationship(
        'Event',
        secondary='event_signups',
        backref='attendees'
    )



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
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    date_time: Mapped[datetime] = mapped_column(db.DateTime, nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=True)
    zipcode: Mapped[str] = mapped_column(String(200), nullable=True)
    link: Mapped[str] = mapped_column(String(300), nullable=True)
    status = db.Column(db.String(20), default="pending")
    group_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("catholic.id"), nullable=True)
    group = db.relationship("Catholic", back_populates="events")

    # ✅ Foreign key to User table
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"), nullable=False)

    # ✅ Relationship
    user = db.relationship("User", backref="events")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "date_time": self.date_time.isoformat(),
            "link": self.link,
            "address": self.address,
            "zipcode": self.zipcode,
            "description": self.description,
            "is_internal": True,
            "add_to_calendar_url": url_for("download_ical", event_id=self.id)
        }


followers = db.Table('followers',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('catholic.id'))
)

# Many-to-many: user <-> event
event_signups = db.Table('event_signups',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'))  # Make sure this matches your model name
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
        new_event = Event(
            title=form.title.data,
            description=form.description.data,
            date_time=datetime.combine(form.date.data, form.time.data),
            group_id=form.group.data,
            link=form.link.data,
            address=form.location.data,
            zipcode=form.location.data,
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

from forms import EventForm  # make sure this import matches your project

@app.route("/calendar", methods=["GET", "POST"])
def calendar_view():
    form = EventForm()
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

@app.route("/add_group", methods=["GET"])
@login_required
def add_group():
    form = GroupForm()
    return render_template("add_group.html", form=form)


@app.route("/submit-group", methods=["POST"])
@login_required
@csrf.exempt
def submit_group():
    form = GroupForm()
    if form.validate_on_submit():
        full_location = f"{form.city.data}, {form.state.data}"

        # Geocode the location
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

        # ❌ Reject if not in New England
        if state_code not in NEW_ENGLAND_STATES:
            flash("❌ Sorry, we are only accepting groups from New England (MA, ME, NH, VT, RI, CT).", "danger")
            return redirect(url_for("groups"))

        new_group = Catholic(
            name=form.name.data,
            city=form.city.data,
            state=state_code,
            zipcode=form.zip_code.data,
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
        full_location = f"{form.city.data}, {form.State.data} {form.zip_code.data or ''}"
        geo_result = geocoder.geocode(full_location)
        lat = lon = None
        state = None
        zip_code = form.zip_code.data or None

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
            zipcode=zip_code,
            lat=lat,
            lon=lon,
            user_id=current_user.id,
            status="pending"
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
    return render_template("groups.html", groups=groups)



@app.route("/event/<int:event_id>/calendar.ics")
def download_ical(event_id):
    event = db.get_or_404(Event, event_id)

    start = event.date_time.strftime("%Y%m%dT%H%M%S")
    end = (event.date_time + timedelta(hours=2)).strftime("%Y%m%dT%H%M%S")
    uid = f"{event.id}@catholicgroups.org"

    ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Catholic Groups//Event Calendar//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{start}
DTSTART:{start}
DTEND:{end}
SUMMARY:{event.title}
DESCRIPTION:{event.description or ''}
LOCATION:{event.address or ''}
END:VEVENT
END:VCALENDAR
"""

    response = make_response(ical)
    response.headers["Content-Disposition"] = f"attachment; filename={event.title}.ics"
    response.headers["Content-Type"] = "text/calendar"
    return response



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
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)

    pending_groups = db.session.execute(
        db.select(Catholic).where(Catholic.status == "pending")
    ).scalars().all()

    pending_events = db.session.execute(
        db.select(Event).where(Event.status == "pending")
    ).scalars().all()

    return render_template("admin_dashboard.html", groups=pending_groups, events=pending_events)

@app.route("/edit-group/<int:group_id>", methods=["GET", "POST"])
@login_required
def edit_group(group_id):
    if not current_user.is_admin:
        abort(403)

    group = db.get_or_404(Catholic, group_id)
    form = GroupForm(obj=group)

    if form.validate_on_submit():
        form.populate_obj(group)
        db.session.commit()
        flash("Group updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_group.html", form=form, group=group)

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

@app.route("/edit-event/<int:event_id>", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    # Logic to load, validate, and update the event
    ...

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



# ---------- RUN ----------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        with app.app_context():
            db.create_all()

            # Create default user for development
            default_user = User.query.filter_by(email="admin@example.com").first()
            if not default_user:
                default_user = User(email="admin@example.com", password="adminpass")
                db.session.add(default_user)
                db.session.commit()

            # Add group if none exist
            if not Catholic.query.first():
                new_group = Catholic(
                    name="St Clement's Group",
                    city="Boston",
                    state="MA",
                    zip_code="02108",  # Make sure to include this if required
                    website_address="http://www.stclementyoungadults.org/",
                    lat=42.347,
                    lon=-71.083,
                    img_url="https://images.squarespace-cdn.com/.../yac.jpg",
                    map_url="https://g.co/kgs/T34keHz",
                    user_id=default_user.id  # ✅ now always valid
                )
                db.session.add(new_group)
                db.session.commit()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=os.getenv("FLASK_ENV") != "production")
