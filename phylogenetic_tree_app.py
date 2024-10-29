from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from ete3 import Tree, TreeStyle, NodeStyle
import random
import os
import uuid
import sys
import threading
import time

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'nwk', 'tre', 'nex', 'phy'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Function to generate a random color
def random_color():
    return "#%06x" % random.randint(0, 0xFFFFFF)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to parse tree file and generate tree visualization
def generate_tree(file_path, tree_type, distance_type, line_thickness, branch_length):
    try:
        with open(file_path, 'r') as file:
            tree_newick = file.read().strip()

        # Create a Tree object
        tree = Tree(tree_newick, format=1)  # format=1 for Newick

        # Define tree style
        tree_style = TreeStyle()
        tree_style.show_leaf_name = True

        # Set tree type
        if tree_type == 'cladogram':
            tree_style.mode = "c"
        elif tree_type == 'phylogram':
            tree_style.mode = "r"
        elif tree_type == 'unrooted':
            tree_style.mode = "u"
        else:
            tree_style.mode = "c"  # Default to cladogram if none specified

        # Set distance type
        try:
            tree_style.branch_vertical_margin = int(distance_type)
        except ValueError:
            tree_style.branch_vertical_margin = 10  # Default distance if input is invalid

        # Iterate through all nodes and assign random colors to branches and leaves
        for node in tree.traverse():
            node_style = NodeStyle()
            node_style['fgcolor'] = random_color()  # Random branch color
            node_style['size'] = 10 if node.is_leaf() else 0  # Size of the node circle (0 for internal nodes)
            node_style['vt_line_color'] = random_color()  # Vertical line color
            node_style['hz_line_color'] = random_color()  # Horizontal line color
            node_style['vt_line_width'] = int(line_thickness)
            node_style['hz_line_width'] = int(line_thickness)
            node.set_style(node_style)
            if branch_length:
                node.dist = float(branch_length)  # Set branch length if specified

        # Render the tree to an image file with high resolution
        unique_filename = f"phylogenetic_tree_{uuid.uuid4().hex}.png"
        output_file = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        tree.render(output_file, w=3000, dpi=300, tree_style=tree_style)  # Increase width and DPI for high-quality output

        return output_file
    except Exception as e:
        return str(e)

# Route to upload file and generate tree
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If user does not select file, browser may also submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            tree_type = request.form.get('tree_type')
            distance_type = request.form.get('distance')
            line_thickness = request.form.get('line_thickness')
            branch_length = request.form.get('branch_length')
            output_file = generate_tree(file_path, tree_type, distance_type, line_thickness, branch_length)
            if output_file.endswith('.png') and os.path.exists(output_file):
                # Restart the server in a new thread before returning the result
                threading.Thread(target=restart_server).start()
                return render_template('result.html', tree_image=url_for('uploaded_file', filename=os.path.basename(output_file)))
            else:
                flash("Error generating tree: " + output_file)  # Display the error message
                return redirect(request.url)
    return render_template('upload.html')

# Route to serve the generated image
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Function to restart the server
def restart_server():
    time.sleep(1)
    os.execv(sys.executable, ['python'] + sys.argv)

# Main function to run the Flask app
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
