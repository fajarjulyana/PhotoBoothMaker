import os
import io
import uuid
import base64
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

# CUPS handler implementation
try:
    import cups
    logging.info("CUPS module imported successfully")
    
    # Test connection with CUPS
    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
        logging.info(f"CUPS connected successfully. Available printers: {printers.keys()}")
        CUPS_AVAILABLE = True
    except Exception as e:
        logging.error(f"Error connecting to CUPS: {str(e)}")
        CUPS_AVAILABLE = False
        cups_connection_error = str(e)
except ImportError as e:
    logging.error(f"Error importing CUPS module: {str(e)}")
    CUPS_AVAILABLE = False
    cups_connection_error = str(e)

# Implementasi dummy untuk cups jika tidak tersedia
if not CUPS_AVAILABLE:
    logging.warning(f"CUPS not available, using dummy implementation. Error: {cups_connection_error if 'cups_connection_error' in locals() else 'Unknown error'}")
    
    class DummyCups:
        def __init__(self):
            logging.info("Initializing dummy CUPS implementation")
            
        def getPrinters(self):
            logging.info("Getting printers from dummy CUPS")
            return {"Default": {"printer-state": 3, "device-uri": "dummy://", "printer-info": "Dummy Printer"}}
            
        def getJobs(self):
            logging.info("Getting jobs from dummy CUPS")
            return {}
            
        def printFile(self, printer_name, file_path, job_name, options):
            logging.info(f"Dummy printing file {file_path} to printer {printer_name}")
            # Hanya simulasi pencetakan dengan mengembalikan ID job acak
            import random
            job_id = random.randint(1000, 9999)
            logging.info(f"Dummy job created with ID: {job_id}")
            return job_id
            
        def cancelJob(self, printer_name, job_id):
            logging.info(f"Dummy canceling job {job_id} on printer {printer_name}")
            pass
    
    # Buat objek cups Connection palsu jika tidak tersedia
    class DummyCupsModule:
        @staticmethod
        def Connection():
            return DummyCups()
    
    # Replace cups module with dummy implementation
    if 'cups' not in locals() or 'cups' not in globals():
        cups = DummyCupsModule
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont

from main import app, db, login_manager
from models import User, Frame, PrintJob, PhotoSession, Photo

# Configure the upload folders if not already in app.config
if 'UPLOAD_FOLDER' not in app.config:
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    app.config['FRAMES_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'frames')
    app.config['PHOTOS_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'photos')
    
    # Ensure directories exist
    os.makedirs(app.config['FRAMES_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PHOTOS_FOLDER'], exist_ok=True)

# Helper functions
def allowed_file(filename):
    """Check if a file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    """Load a user from the database"""
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    """Render the main photo booth page"""
    # Get active frames for the frame selector
    frames = Frame.query.filter_by(is_active=True).all()
    
    # Get available printers
    printers = {}
    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
    except Exception as e:
        logging.warning(f"Error connecting to CUPS: {str(e)}")
    
    return render_template('index.html', frames=frames, printers=printers)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout the current user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    """Admin dashboard"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
        
    return render_template('admin/index.html')

@app.route('/admin/frames')
@login_required
def admin_frames():
    """Manage frames"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    frames = Frame.query.order_by(Frame.created_at.desc()).all()
    return render_template('admin/frames.html', frames=frames)

@app.route('/admin/frame/add', methods=['POST'])
@login_required
def add_frame():
    """Add a new frame"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        is_active = True if request.form.get('is_active') else False
        
        # Get settings
        offset_x = request.form.get('offset_x', 0, type=int)
        offset_y = request.form.get('offset_y', 0, type=int)
        scale = request.form.get('scale', 1.0, type=float)
        
        # Check if a file was uploaded
        if 'frame_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('admin_frames'))
            
        file = request.files['frame_file']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('admin_frames'))
            
        if file and allowed_file(file.filename):
            # Save the file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(app.config['FRAMES_FOLDER'], new_filename)
            file.save(file_path)
            
            # Create a thumbnail
            thumb_filename = f"thumb_{new_filename}"
            thumb_path = os.path.join(app.config['FRAMES_FOLDER'], thumb_filename)
            
            try:
                with Image.open(file_path) as img:
                    img.thumbnail((200, 200))
                    img.save(thumb_path)
                    
                # Create frame record
                frame = Frame(
                    name=name,
                    description=description,
                    file_path=os.path.join('uploads', 'frames', new_filename),
                    thumbnail_path=os.path.join('uploads', 'frames', thumb_filename),
                    is_active=is_active,
                    creator_id=current_user.id,
                    settings={
                        'offset_x': offset_x,
                        'offset_y': offset_y,
                        'scale': scale
                    }
                )
                
                db.session.add(frame)
                db.session.commit()
                
                flash('Frame added successfully', 'success')
                
            except Exception as e:
                # Clean up files if there was an error
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
                    
                logging.error(f"Error creating thumbnail: {str(e)}")
                flash(f'Error creating thumbnail: {str(e)}', 'danger')
        else:
            flash('Invalid file type. Please upload an image file (PNG, JPG, JPEG, GIF)', 'danger')
            
    except Exception as e:
        logging.error(f"Error adding frame: {str(e)}")
        flash(f'Error adding frame: {str(e)}', 'danger')
        
    return redirect(url_for('admin_frames'))

@app.route('/admin/frame/<int:frame_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_frame(frame_id):
    """Edit a frame"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    frame = Frame.query.get_or_404(frame_id)
    
    if request.method == 'POST':
        try:
            frame.name = request.form.get('name')
            frame.description = request.form.get('description')
            frame.is_active = True if request.form.get('is_active') else False
            
            # Update settings
            settings = frame.settings or {}
            settings['offset_x'] = request.form.get('offset_x', 0, type=int)
            settings['offset_y'] = request.form.get('offset_y', 0, type=int)
            settings['scale'] = request.form.get('scale', 1.0, type=float)
            frame.settings = settings
            
            # Check if a new file was uploaded
            if 'frame_file' in request.files and request.files['frame_file'].filename != '':
                file = request.files['frame_file']
                
                if allowed_file(file.filename):
                    # Save the new file
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    new_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(app.config['FRAMES_FOLDER'], new_filename)
                    file.save(file_path)
                    
                    # Create a new thumbnail
                    thumb_filename = f"thumb_{new_filename}"
                    thumb_path = os.path.join(app.config['FRAMES_FOLDER'], thumb_filename)
                    
                    with Image.open(file_path) as img:
                        img.thumbnail((200, 200))
                        img.save(thumb_path)
                    
                    # Delete old files
                    old_file_path = os.path.join(app.root_path, 'static', frame.file_path)
                    old_thumb_path = os.path.join(app.root_path, 'static', frame.thumbnail_path) if frame.thumbnail_path else None
                    
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                    if old_thumb_path and os.path.exists(old_thumb_path):
                        os.remove(old_thumb_path)
                    
                    # Update frame paths
                    frame.file_path = os.path.join('uploads', 'frames', new_filename)
                    frame.thumbnail_path = os.path.join('uploads', 'frames', thumb_filename)
                else:
                    flash('Invalid file type. Please upload an image file (PNG, JPG, JPEG, GIF)', 'danger')
                    return redirect(url_for('edit_frame', frame_id=frame.id))
            
            db.session.commit()
            flash('Frame updated successfully', 'success')
            return redirect(url_for('admin_frames'))
            
        except Exception as e:
            logging.error(f"Error updating frame: {str(e)}")
            flash(f'Error updating frame: {str(e)}', 'danger')
    
    return render_template('admin/edit_frame.html', frame=frame)

@app.route('/admin/frame/<int:frame_id>/delete', methods=['POST'])
@login_required
def delete_frame(frame_id):
    """Delete a frame"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    frame = Frame.query.get_or_404(frame_id)
    
    try:
        # Delete the files
        file_path = os.path.join(app.root_path, 'static', frame.file_path)
        thumb_path = os.path.join(app.root_path, 'static', frame.thumbnail_path) if frame.thumbnail_path else None
        
        if os.path.exists(file_path):
            os.remove(file_path)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
        
        # Delete the database record
        db.session.delete(frame)
        db.session.commit()
        
        flash('Frame deleted successfully', 'success')
        
    except Exception as e:
        logging.error(f"Error deleting frame: {str(e)}")
        flash(f'Error deleting frame: {str(e)}', 'danger')
    
    return redirect(url_for('admin_frames'))

@app.route('/admin/printers')
@login_required
def admin_printers():
    """Manage printers"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    # Get available printers from CUPS
    conn = cups.Connection()
    printers = conn.getPrinters()
    
    return render_template('admin/printers.html', printers=printers)

@app.route('/process_photo_strip', methods=['POST'])
def process_photo_strip():
    """Process and create a photo strip from the uploaded images"""
    try:
        data = request.get_json()
        
        # Get the base64 encoded images
        photos = data.get('photos', [])
        if not photos:
            return jsonify({'error': 'No photos provided'}), 400
        
        # Get template style and number of photos
        template_style = data.get('templateStyle', 'classic')
        frame_id = data.get('frameId')
        
        # Create the photo strip based on the template
        photo_strip = create_photo_strip(photos, template_style, frame_id)
        
        # Convert the final image to base64 for sending back to client
        buffered = io.BytesIO()
        photo_strip.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Create a session to store these photos
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            
        photo_session = PhotoSession.query.filter_by(session_id=session['session_id']).first()
        if not photo_session:
            photo_session = PhotoSession(session_id=session['session_id'])
            db.session.add(photo_session)
            db.session.commit()
        
        return jsonify({'photo_strip': img_str, 'session_id': session['session_id']})
    
    except Exception as e:
        logging.error(f"Error processing photo strip: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@app.route('/print_photo_strip', methods=['POST'])
def print_photo_strip():
    """Create a PDF for printing from the photo strip and send to printer via CUPS"""
    try:
        from PyPDF2 import PdfWriter, PdfReader
        from io import BytesIO
        
        data = request.get_json()
        photo_strip_data = data.get('photoStrip')
        printer_name = data.get('printerName')
        
        if not photo_strip_data:
            return jsonify({'error': 'No photo strip data provided'}), 400
        
        # Remove the data URL prefix if present
        if 'data:image/' in photo_strip_data:
            photo_strip_data = photo_strip_data.split(',')[1]
        
        # Decode the base64 data
        image_data = base64.b64decode(photo_strip_data)
        
        # Save the image as both JPG (for reference) and PDF (for printing)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        jpg_filename = f"photobooth_print_{timestamp}.jpg"
        pdf_filename = f"photobooth_print_{timestamp}.pdf"
        
        # Make sure the directory exists
        os.makedirs(app.config['PHOTOS_FOLDER'], exist_ok=True)
        
        jpg_path = os.path.join(app.config['PHOTOS_FOLDER'], jpg_filename)
        pdf_path = os.path.join(app.config['PHOTOS_FOLDER'], pdf_filename)
        
        # Save the JPG version
        with open(jpg_path, 'wb') as f:
            f.write(image_data)
        
        # Create PDF from the image
        try:
            # Open the image with PIL
            image = Image.open(BytesIO(image_data))
            
            # Create a temporary BytesIO object to save the PDF
            pdf_buffer = BytesIO()
            
            # Convert the image to PDF and save to the buffer
            image.save(pdf_buffer, format='PDF', resolution=300.0)
            
            # Write the PDF to a file
            with open(pdf_path, 'wb') as f:
                f.write(pdf_buffer.getvalue())
            
            logging.info(f"PDF created successfully at: {pdf_path}")
            
            # Generate absolute file path for printing
            abs_pdf_path = os.path.abspath(pdf_path)
            logging.info(f"Absolute PDF path: {abs_pdf_path}")
            
            # Try to print via CUPS if available
            cups_job_id = None
            cups_error = None
            status = 'ready_to_print'
            
            if CUPS_AVAILABLE and printer_name:
                try:
                    logging.info(f"Attempting to print to {printer_name} via CUPS")
                    conn = cups.Connection()
                    job_title = f"PhotoBooth Print {timestamp}"
                    
                    # Print options for optimal photo quality
                    options = {
		    'media': 'A4',
		    'PageSize': 'A4',
		    'MediaType': 'PhotographicGlossy',  # Pilih jenis kertas glossy
		    'fit-to-page': 'true',              # Pastikan gambar pas dengan halaman
		    'print-quality': 'High',             # Cetak dengan kualitas tinggi
		    'sides': 'one-sided',                # Cetak satu sisi
		    'print-color-mode': 'color',         # Cetak berwarna
		    'Resolution': '1200dpi',             # Resolusi tinggi
		    'PrintoutMode': 'photo',             # Mode cetak foto
		    }


                    
                    # Print the PDF
                    cups_job_id = conn.printFile(
                        printer_name, 
                        abs_pdf_path, 
                        job_title, 
                        options
                    )
                    
                    logging.info(f"CUPS job created with ID: {cups_job_id}")
                    status = 'printing'
                except Exception as e:
                    cups_error = str(e)
                    logging.error(f"CUPS printing error: {cups_error}")
                    status = 'failed'
            else:
                if not CUPS_AVAILABLE:
                    cups_error = "CUPS printing not available"
                    logging.warning(cups_error)
                elif not printer_name:
                    cups_error = "No printer specified"
                    logging.warning(cups_error)
            
            # Create a print job record in the database
            print_job = PrintJob(
                file_path=os.path.join('uploads', 'photos', pdf_filename),
                printer_name=printer_name or "Manual Print",
                status=status,
                cups_job_id=cups_job_id,
                error_message=cups_error
            )
            db.session.add(print_job)
            db.session.commit()
            
            # Generate URLs for both JPG and PDF
            pdf_url = url_for('static', filename=os.path.join('uploads', 'photos', pdf_filename))
            jpg_url = url_for('static', filename=os.path.join('uploads', 'photos', jpg_filename))
            
            response = {
                'success': True, 
                'message': "Photo strip saved and print job created",
                'job_id': print_job.id,
                'pdf_url': pdf_url,
                'jpg_url': jpg_url
            }
            
            # Add cups status info to response
            if cups_job_id:
                response['cups_job_id'] = cups_job_id
                response['print_status'] = 'printing'
            elif cups_error:
                response['cups_error'] = cups_error
                response['print_status'] = 'failed'
            
            return jsonify(response)
            
        except Exception as e:
            logging.error(f"Error creating PDF: {str(e)}")
            logging.exception(e)
            return jsonify({'error': f"Error creating PDF: {str(e)}"}), 500
    
    except Exception as e:
        logging.error(f"Error processing print request: {str(e)}")
        logging.exception(e)
        return jsonify({'error': str(e)}), 500
        
@app.route('/admin/print_jobs')
@login_required
def admin_print_jobs():
    """View print jobs"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    print_jobs = PrintJob.query.order_by(PrintJob.created_at.desc()).all()
    
    # Get status of active print jobs
    conn = cups.Connection()
    active_jobs = {}
    try:
        active_jobs = conn.getJobs()
    except Exception as e:
        logging.error(f"Error getting active print jobs: {str(e)}")
    
    return render_template('admin/print_jobs.html', print_jobs=print_jobs, active_jobs=active_jobs)

@app.route('/admin/print_job/<int:job_id>/cancel', methods=['POST'])
@login_required
def cancel_print_job(job_id):
    """Cancel a print job"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    print_job = PrintJob.query.get_or_404(job_id)
    
    # Cancel the job in CUPS if it's still active
    if print_job.cups_job_id and print_job.status == 'printing':
        try:
            conn = cups.Connection()
            conn.cancelJob(printer_name=print_job.printer_name, job_id=print_job.cups_job_id)
        except Exception as e:
            logging.error(f"Error canceling print job: {str(e)}")
    
    # Update the status in the database
    print_job.status = 'canceled'
    db.session.commit()
    
    flash('Print job canceled', 'success')
    return redirect(url_for('admin_print_jobs'))

def apply_frame_to_image(image, frame_id):
    """
    Apply a frame to an individual image
    
    Args:
        image: PIL Image object
        frame_id: ID of the frame to apply
        
    Returns:
        PIL Image object with the frame applied
    """
    # If no frame is selected, return the original image
    if not frame_id:
        return image
    
    # Get the frame from the database
    frame = Frame.query.get(frame_id)
    if not frame:
        logging.warning(f"Frame with ID {frame_id} not found")
        return image
    
    # Load the frame image
    try:
        logging.debug(f"Loading frame from path: {frame.file_path}")
        frame_path = os.path.join(app.root_path, 'static', frame.file_path)
        
        # Check if file exists
        if not os.path.exists(frame_path):
            logging.error(f"Frame file does not exist: {frame_path}")
            return image
            
        frame_img = Image.open(frame_path).convert('RGBA')
        logging.debug(f"Frame loaded successfully, size: {frame_img.size}")
        
        # Get frame settings
        settings = frame.settings or {}
        offset_x = settings.get('offset_x', 0)
        offset_y = settings.get('offset_y', 0)
        scale = settings.get('scale', 1.0)
        
        # Resize frame to match the size of the input image
        # This ensures the frame properly overlays the photo
        new_width = image.width
        new_height = image.height
        frame_img = frame_img.resize((new_width, new_height), Image.LANCZOS)
        
        # Ensure the image is in RGBA mode to support transparency
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create a new composite image by copying the original
        new_img = image.copy()
        
        # Overlay the frame on top of the image
        # The alpha channel of the frame will control transparency
        new_img.paste(frame_img, (0, 0), frame_img)
        
        logging.debug("Frame applied successfully")
        
        # Convert back to RGB for compatibility
        return new_img.convert('RGB')
        
    except Exception as e:
        logging.error(f"Error applying frame: {str(e)}")
        logging.exception(e)
        return image

def create_photo_strip(photos, template_style, frame_id=None):
    """
    Create a photo strip based on the provided photos and template style
    
    Args:
        photos: List of base64 encoded images
        template_style: The style of the template to use
        frame_id: ID of the frame to apply to each photo (optional)
    
    Returns:
        PIL Image object of the final photo strip
    """
    logging.debug("Creating photo strip with template style: %s, frame_id: %s", template_style, frame_id)
    
    # Decode the base64 images
    image_objects = []
    for photo_data in photos:
        # Remove the data URL prefix if present
        if 'data:image/' in photo_data:
            photo_data = photo_data.split(',')[1]
        
        # Decode the base64 data
        image_data = base64.b64decode(photo_data)
        image = Image.open(io.BytesIO(image_data))
        
        # Apply frame if specified
        if frame_id:
            image = apply_frame_to_image(image, frame_id)
            
        image_objects.append(image)
    
    num_photos = len(image_objects)
    
    # 2R dimensions in pixels at 300 DPI
    photo_width_2r = 709
    photo_height_2r = 1063
    
    # Use 2R as the base size, but we'll put multiple photos on one sheet
    a4_width = 2480
    a4_height = 3508
    
    # Set photo dimensions based on template style - for 2R size (6x9cm)
    if template_style == 'classic':
        photo_width = photo_width_2r  # Use the 2R width directly
        margin_between = 20
        background_color = (255, 255, 255)
        
    elif template_style == 'modern':
        photo_width = photo_width_2r
        margin_between = 30
        background_color = (240, 240, 240)
        
    elif template_style == 'vintage':
        photo_width = photo_width_2r
        margin_between = 25
        background_color = (245, 235, 215)
        
    else:  # Default to classic
        photo_width = photo_width_2r
        margin_between = 20
        background_color = (255, 255, 255)
    
    # Create a new A4 image
    photo_strip = Image.new('RGB', (a4_width, a4_height), background_color)
    draw = ImageDraw.Draw(photo_strip)
    
    # Add a title to the photo strip
    try:
        title_size = 120
        try:
            font = ImageFont.truetype("arial.ttf", title_size)
        except:
            font = ImageFont.load_default()
            
        title = "Fajar Mandiri Photo Booth"
        title_y = 150  # Top margin for title
        draw.text((a4_width // 2, title_y), title, fill=(0, 0, 0), font=font, anchor="mm")
    except Exception as e:
        logging.warning(f"Font issue, skipping title: {str(e)}")
    
    # Set top margin for photos
    start_y = 300  # Fixed margin from the top
    current_y = start_y
    
    # Add each photo to the strip
    for i, image in enumerate(image_objects):
        aspect_ratio = image.width / image.height
        new_width = photo_width
        new_height = int(new_width / aspect_ratio)
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        
        x_position = (a4_width - resized_image.width) // 2
        photo_strip.paste(resized_image, (x_position, current_y))
        
        # Add photo number
        try:
            number_font_size = 120
            try:
                number_font = ImageFont.truetype("arial.ttf", number_font_size)
            except:
                number_font = ImageFont.load_default()
                
            number_text = f"#{i+1}"
            number_x = x_position + 40
            number_y = current_y + 40
            
            draw.text((number_x, number_y), number_text, fill=(255, 255, 255), font=number_font)
        except Exception as e:
            logging.warning(f"Error adding photo number: {str(e)}")
        
        current_y += resized_image.height + margin_between
    
    logging.debug("Photo strip created successfully")
    return photo_strip


@app.route('/download_strip', methods=['POST'])
def download_strip():
    """Generate and download the photo strip"""
    try:
        data = request.get_json()
        photo_strip_data = data.get('photoStrip')
        
        # Remove the data URL prefix if present
        if 'data:image/' in photo_strip_data:
            photo_strip_data = photo_strip_data.split(',')[1]
        
        # Decode the base64 data
        image_data = base64.b64decode(photo_strip_data)
        
        # Create a file-like object from the decoded image data
        img_io = io.BytesIO(image_data)
        img_io.seek(0)
        
        # Generate a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photobooth_{timestamp}.jpg"
        
        return send_file(
            img_io,
            as_attachment=True,
            download_name=filename,
            mimetype='image/jpeg'
        )
        
    except Exception as e:
        logging.error(f"Error downloading photo strip: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
