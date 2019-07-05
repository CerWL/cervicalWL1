import glob
import ntpath
import os
import shutil
import numpy as np
import pandas as pd
import cv2
import multiprocessing as mp

DEBUG = False
DEBUG_PATH = './Debug_DF'

def resize_img(img, resize_ratio):
    if (resize_ratio == 1) or (resize_ratio <=0):
        return img
    else:
        h, w, _ = img.shape
        img = cv2.resize(img, (int(w * resize_ratio), int(h * resize_ratio)))
    return img

def get_intensity(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    return np.average(img[:,:,0])

def wrapper(arg):
    images = arg['images_split']
    SEGMENT_TEST_DIR =  arg['segment_test_dir']
    DENOISING =  arg['denoising']
    FILE_PATTERN = arg['file_pattern']
    RESIZE_RATIO = arg['resize_ratio']
    print(images)
    res = pd.DataFrame()
    for source in images:
        filename = ntpath.basename(source)
        path_split = source.split('/')
        slide_name = path_split[-3] if path_split[-2] == 'Images' else path_split[-2]
        base_filename = slide_name + '_' + os.path.splitext(filename)[0]
        df_dic = {'FOV_Name': base_filename}
        print(base_filename)

        base_outdir = os.path.join('{}/{}/images'.format(SEGMENT_TEST_DIR, base_filename))
        if not os.path.exists(base_outdir): os.makedirs(base_outdir)

        target = os.path.join(base_outdir, base_filename+'.png')

        if DENOISING:
            img = cv2.imread(source)
            if DEBUG:
                df_dic['OG_Intens'] = get_intensity(img)
            img = resize_img(img, RESIZE_RATIO)
            if DEBUG:
                df_dic['RS_Intens'] = get_intensity(img)
            img_dn = cv2.fastNlMeansDenoisingColored(img, None, 7, 7, 7, 21)
            if DEBUG:
                df_dic['DN_Intens'] = get_intensity(img)
            cv2.imwrite(target, img_dn)
            print("Color image %s denoising & copy complete!" % filename)
        elif (FILE_PATTERN != '*.png') or (RESIZE_RATIO != 1):
            img = cv2.imread(source)
            if DEBUG:
                df_dic['OG_Intens'] = get_intensity(img)
            img = resize_img(img, RESIZE_RATIO)
            if DEBUG:
                 df_dic['RS_Intens'] = get_intensity(img)
                 df_dic['DN_Intens'] = np.nan
            cv2.imwrite(target, img)
            print(source, target)
            print("Image %s copy complete." % filename)
        else:
            if DEBUG:
                img = cv2.imread(source)
                df_dic['OG_Intens'] = get_intensity(img)
                df_dic['RS_Intens'] = np.nan
                df_dic['DN_Intens'] = np.nan
            print(source, target)
            shutil.copy(source, target)
            print("Color image %s copy complete!" % filename)

        if DEBUG:
            res = res.append(pd.DataFrame(df_dic, index=[0]))
            res = res.reset_index(drop=True)

    if DEBUG:
        return res
    else:
        return None

def process_origin_image(DATASETS_DIR, SEGMENT_TEST_DIR, FILE_PATTERN, DENOISING, RESIZE_RATIO):
    global STAST_DF
    #FILE_PATTERN = '*.png'

    # Split train set
    total_images = np.sort(glob.glob(os.path.join(DATASETS_DIR, FILE_PATTERN)))
    print(total_images)

    if DEBUG:
        STAST_DF['FOV_Path'] = total_images
        STAST_DF['FOV_Name'] = STAST_DF['FOV_Path'].map(lambda x: os.path.basename(x).split('.')[0])
        STAST_DF['Slide_Path'] = DATASETS_DIR
        print(len(STAST_DF))

    cpus = mp.cpu_count()
    images_split = np.array_split(total_images, cpus)
    images_split2 = []

    for _images_split in images_split:
        images_split2.append({'images_split': _images_split, 'segment_test_dir': SEGMENT_TEST_DIR, "denoising": DENOISING, "file_pattern": FILE_PATTERN, 'resize_ratio': RESIZE_RATIO})

    p = mp.Pool(processes=cpus)
    res = p.map(wrapper, images_split2)
    p.close()
    p.join()

    if DEBUG:
        res = pd.concat(res)
        STAST_DF = STAST_DF.merge(res, on='FOV_Name')
        STAST_DF['RS_Ratio'] = RESIZE_RATIO
        print(STAST_DF)

def step1v2(origindir, segtestdir, filepattern, debug=False):
    DATASETS_DIR = origindir
    SEGMENT_TEST_DIR = segtestdir
    FILE_PATTERN = filepattern

    DENOISING = False
    RESIZE_RATIO = 1

    if DEBUG:
        #OG_Intens: Original FOV Intensity
        #DN_Intens: Denoised FOV Intensity
        #RS_Intens: Resized FOV Intensity
        #df_columns = ['Slide_Path', 'Fov_Path', 'Fov_Name', 'OG_Intens', 'RS_Intens', 'DN_Intens', 'RS_Ratio']
        df_columns = ['Slide_Path', 'Fov_Path', 'Fov_Name']
        STAST_DF = pd.DataFrame()

    process_origin_image(origindir, segtestdir, filepattern, DENOISING, RESIZE_RATIO)

    if DEBUG:
        if not os.path.exists(DEBUG_PATH):
            os.makedirs(DEBUG_PATH)
        STAST_DF.to_csv(os.path.join(DEBUG_PATH, 'step1.csv'))
