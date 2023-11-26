from flask import Flask, render_template, request, redirect, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import string
import random
import segno
from flask import abort

app = Flask(__name__, template_folder="templates")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    long_url = db.Column(db.String(255), nullable=False)
    short_code = db.Column(db.String(30), unique=True, nullable=False)

    def __init__(self, long_url, short_code):
        self.long_url= long_url
        self.short_code=short_code


def start_db():
    with app.app_context():
        db.create_all()


# Initialize the database within the application context
start_db()


def generate_short_code():
    characters = string.ascii_letters + string.digits
    short_code = ''.join(random.choice(characters) for _ in range(6))
    return short_code.upper()


def generate_qr_code(url):
    qr_code = segno.make(url)
    return qr_code


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/shorten', methods=['POST'])
def shorten_url():
    try:
        long_url = request.form.get('long_url')
        customize_code = request.form.get('customize_code')

        # Check if the custom code already exists
        if customize_code and URL.query.filter_by(short_code=customize_code).first():
            return jsonify({"error": "Custom code already exists."}), 400

        short_code = customize_code if customize_code else generate_short_code()

        # Save to the database
        new_url = URL(long_url, short_code)
        db.session.add(new_url)
        db.session.commit()

        return jsonify({"shortened_url": short_code, "link": f"{request.host_url}{short_code}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/list', methods=['GET', 'POST'])
def list_urls():
    urls = URL.query.all()
    url_list = [{"short_code": url.short_code, "long_url": url.long_url,
                 "qr_code": generate_qr_code('http://127.0.0.1:5000/'+url.short_code)} for url in urls]
    return render_template('table.html', urls_data=url_list)




@app.route('/test', methods=['GET'])
def test_short_url():
    short_code = request.args.get('short_code')
    if short_code:
        # Check if the short code exists in the database
        url = URL.query.filter_by(short_code=short_code).first()
        if url:
            return jsonify({"success": True, "long_url": url.long_url})
        else:
            return jsonify({"success": False, "error": "Short code not found"}), 404
    else:
        return jsonify({"success": False, "error": "Missing short code parameter"}), 400


@app.route('/<short_code>', methods=['GET'])
def redirect_to_original_url(short_code):
    # Find the URL in the database based on the short code
    url_entry = URL.query.filter_by(short_code=short_code.upper()).first()

    if url_entry:
        # Redirect to the original URL
        return redirect(url_entry.long_url)
    else:
        # If the short code doesn't exist, return a 404 error
        abort(404)


if __name__ == "__main__":
    try:
        app.run(debug=True)
    except Exception as e:
        print(f"An error occurred: {str(e)}")