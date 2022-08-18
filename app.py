from crypt import methods
from flask import Flask, flash, render_template, request
from flask import redirect, send_from_directory, url_for, send_file
from werkzeug.utils import secure_filename
import layoutparser as lp
import cv2
import os
from glob import glob
from io import BytesIO
from zipfile import ZipFile
import base64
import json
import re
from run import img_cap
import easyocr


image_path = []
images = []

result_cv = []
result_en = []
result_meta = []

page_name = []
page_uri = []
download_name = []
meta_data = []
json_conv = []


det_co = {}
global manual_coor
captions = []
session = 0

def clear_lists():
    image_path.clear()
    images.clear()
    
    result_cv.clear()
    result_en.clear()
    result_meta.clear()
    
    page_name.clear()
    download_name.clear()
    meta_data.clear()
    json_conv.clear()

    page_uri.clear() 

def ocrPage(pages):
    reader = easyocr.Reader(['ar'])
    results = []
    for page in pages:
        result = reader.readtext(page, detail = 0)
        results.append(result)
    return results

def get_page_metadata():

    for page in page_name:

        curr_dict_meta = {}
        
        curr_metadata = re.split("[- |_ | |.]", page)
        
        # we need one that generalizes if it is not the same as the ones that we have
        curr_dict_meta['name'] = curr_metadata[0] + '_' + curr_metadata[1]

        count = 0
        for i in curr_metadata:

            if(len(i) == 4 and i.isnumeric()):
                curr_dict_meta['issue_date'] = i

            if( (len(i) < 4) and i.isnumeric() and count != len(curr_metadata) - 2):
                curr_dict_meta['issue'] = i

            if("iss" in i):
                curr_dict_meta['issue'] = i[3:]

            if(count == len(curr_metadata) - 2):
                curr_dict_meta['page'] = i

            count += 1
        meta_data.append(curr_dict_meta) 
        

def get_whole_pages_detections(model):
    """
    take the model and the pages as input
    and returns the detections that are made by the model
    on each page (each page has one element in the detections list)
    """
    detections = []
    for i in range(len(image_path)):
        images.append(cv2.imread(image_path[i]))
        layout = model.detect(images[i])
        detections.append(layout)
        
    return detections


def get_detections_coor(detections):

    # coordinates is the coordinates of each image detection in a page
    # page detections is the number of detections for each page
    coordinates = []
    page_detections = []
    
    for i in range(len(detections)):
        # number is to keep track of the detections in the current page
        number = 0
        for j in range(len(detections[i])):
        
            # we should be now in the index of a certain text block
            curr_block = detections[i][j].block
            curr_img_coordinates = {}
        
            curr_img_coordinates['x_1'] = int(curr_block.x_1)
            curr_img_coordinates['x_2'] = int(curr_block.x_2)
            curr_img_coordinates['y_1'] = int(curr_block.y_1)
            curr_img_coordinates['y_2'] = int(curr_block.y_2)
        
            coordinates.append(curr_img_coordinates)
            
            number += 1
        page_detections.append(number)

    return coordinates, page_detections


def get_detections_images(coordinates, no_page_detections):
    # showing the images
    pages_pointer = 0
    page_detections_pointer = 0
    det_co[pages_pointer] = []
    for i in range(len(coordinates)):
        if(page_detections_pointer == no_page_detections[pages_pointer]):
            pages_pointer += 1
            page_detections_pointer = 0
            det_co[pages_pointer] = []
  
                    
        #extracting the image
        x_1 = coordinates[i]['x_1']
        x_2 = coordinates[i]['x_2']
        y_1 = coordinates[i]['y_1']
        y_2 = coordinates[i]['y_2']
        
        det_co[pages_pointer].append(coordinates[i])
        curr_crop_img = images[pages_pointer][y_1:y_2, x_1:x_2]
        # captions.append(img_cap(curr_crop_img))
        result_cv.append({"page": pages_pointer, "obj":curr_crop_img, "index":page_detections_pointer})
        result_meta.append({"page": pages_pointer, "obj":meta_data[pages_pointer], "index":page_detections_pointer})
        download_name.append({"page": pages_pointer, "obj":page_name[pages_pointer], "index":page_detections_pointer})
        page_detections_pointer += 1


def create_detections():  
    model = lp.Detectron2LayoutModel("lp://NewspaperNavigator/faster_rcnn_R_50_FPN_3x/config",
                                label_map={0: "Photograph", 1: "Illustration", 2: "Map",
                                            3: "Comics/Cartoon", 4: "Editorial Cartoon", 5: "Headline",
                                            6: "Advertisement"}) 
    detections = get_whole_pages_detections(model)

    coordinates, page_detections = get_detections_coor(detections)

    get_detections_images(coordinates, page_detections)
    # now we have the results in result_cv


def ndarray_to_b64(ndarray):
    result_en.clear()
    for i in ndarray:
        _, buffer = cv2.imencode('.png', i['obj'])
        im_en = base64.b64encode(buffer).decode('utf-8')  
        result_en.append({"page": i['page'], "obj":im_en, "index":i['index']})


def save_ndImages():
    count = 0
    for i in range(len(result_cv)):
        os.chdir(download_folder)
        
        if(i != 0 and download_name[i]['obj'] != download_name[i-1]['obj']):
            count = 0

        split_name = download_name[i]['obj'].split('.')
        result_name = split_name[0] + '_' + str(count) + '.' + split_name[1]
        cv2.imwrite(result_name, result_cv[i]['obj'])
        count += 1


def getImgCap():

    imgCapRes = img_cap(result_cv)

    for i in imgCapRes:
        del i[-5:-1]
    return imgCapRes
    
    # 3 captions for each image are created
    # They are in the form of a list




app = Flask(__name__, static_folder="static")
app.secret_key = "super secret key"
ALLOWED_EXTENSIONS = {'jpg', 'png', 'jpeg'}
UPLOAD_FOLDER = "/home/ahmed_fathi/P2E/Page2Elements/static"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
download_folder = "/home/ahmed_fathi/P2E/Page2Elements/download"

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def upload_image():
    global session
    session = 0
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        files = request.files.getlist("file")
        up_count = 0
        clear_lists()
        for f in files:
            if f.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if allowed_file(f.filename):
                file_name = secure_filename(f.filename)
                cv_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
                f.save(cv_path)
                image_path.append(cv_path)
                page_name.append(file_name)
                up_count += 1
        if up_count == len(files):
            get_page_metadata()
            return redirect(url_for('metadata'))
        if 0 < up_count < len(files):
            return redirect(request.url)
    return render_template('upload.html')


@app.route('/detections', methods=['GET', 'POST'])
def detections():
    global session
    if session == 0:
        create_detections()
        session = 1
    # ocr_page = ocrPage(images)
    ndarray_to_b64(result_cv)
    if request.method == 'POST':
        image_index = int(request.get_json())
        print(image_index)
        del det_co[result_en[image_index]['page']][result_en[image_index]['index']]
        del result_en[image_index]
        del result_meta[image_index]
        del result_cv[image_index]
        for i in range(image_index, len(result_en)):
            result_cv[i]["index"] -= 1
            result_en[i]["index"] -= 1
            result_meta[i]["index"] -= 1
    return render_template('detections.html', pass_files=result_en, pass_meta=result_meta, pass_range = range(len(result_en)))


@app.route('/download', methods=['GET', 'POST'])
def download():
    if request.method == 'POST':
        if request.form['download'] == 'Images':
            save_ndImages()
            stream = BytesIO()
            with ZipFile(stream, 'w') as zf:
                for page in page_name:
                    search_name = "%s*.%s" % (page.split('.')[0], page.split('.')[1])
                    for file in glob(os.path.join(download_folder, search_name)):
                        zf.write(file, os.path.basename(file))
            stream.seek(0)
            return send_file(
                stream, 
                as_attachment=True,
                attachment_filename='lib_bot_download_images.zip'
            )

        elif request.form['download'] == 'JSON':
            for i in range(len(result_cv)):
                tmp_dict = {}
                tmp_dict["image"] = result_en[i]['obj']
                tmp_dict["name"] = result_meta[i]['obj']["name"]
                tmp_dict["issue"] = result_meta[i]['obj']["issue"]
                tmp_dict["issue_date"] = result_meta[i]['obj']["issue_date"]
                tmp_dict["page"] = result_meta[i]['obj']["page"]
                json_conv.append(tmp_dict)
            download_json = json.dumps(json_conv)
            os.chdir(download_folder)
            json_download_name = "lib_bot_download_json.json" 
            with open(json_download_name, "w") as outfile:
                outfile.write(download_json)
            return send_from_directory(download_folder, json_download_name, as_attachment=True)
        elif request.form['download'] == "Start New":
            return redirect('/')
        else:
            return render_template('download.html')

    return render_template('download.html')


@app.route('/manual_detections', methods=['POST', 'GET'])
def manual():
    index_manual = 0
    for i in page_name:
        page_uri.append(url_for('static', filename=i))
    if request.method == 'POST':
        manual_coor = request.get_json()
        if (int(manual_coor[0]['sel']) == 1):
            for i in manual_coor:
                #extracting the image
                x_1 = int(float(i['left'][:len(i['left']) - 2])  / i['ratio_w'])
                x_2 = int(float(i['right'][:len(i['right']) - 2])/ i['ratio_w'])
                y_1 = int(float(i['top'][:len(i['top']) - 2]) / i['ratio_h'])
                y_2 = int(float(i['bottom'][:len(i['bottom']) - 2]) / i['ratio_h'])
                index_manual = int(i['index'])
                curr_crop_img = images[index_manual][y_1:y_2, x_1:x_2]
                
                result_cv.append({"page": index_manual, "obj":curr_crop_img, "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
                result_meta.append({"page": index_manual, "obj":meta_data[index_manual], "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
                download_name.append({"page": index_manual, "obj":page_name[index_manual], "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
            return render_template('manual.html', img_src=page_uri, rng_img = range(len(page_name)), det_co = det_co[index_manual], sv_ind = index_manual)
        else:
            index_manual = int(manual_coor[0]['index'])
            return render_template('manual.html', img_src=page_uri, rng_img = range(len(page_name)), det_co = det_co[index_manual], sv_ind = index_manual)
    return render_template('manual.html', img_src=page_uri, rng_img = range(len(page_name)), det_co = det_co[index_manual], sv_ind = index_manual)


@app.route('/metadata', methods=['POST', 'GET'])
def metadata():
    index_meta = 0
    for i in page_name:
        page_uri.append(url_for('static', filename=i))       
    meta_request = request.get_json()
    if request.method == 'POST':
        if (int(meta_request[0]['write']) == 1):
            return 
        else:
            index_meta = int(meta_request[0]['index'])
            return render_template('meta_data.html', page_uri=page_uri, rng_img = range(len(page_name)), index_meta = index_meta, meta_data=meta_data)
    return render_template('meta_data.html', page_uri=page_uri, rng_img = range(len(page_name)), index_meta = index_meta, meta_data=meta_data)


if __name__ == "__main__":
    app.run(debug=True)
