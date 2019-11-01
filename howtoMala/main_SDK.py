#!/usr/bin/env python
# coding: utf-8
import time, os, shutil, cv2, json
import pandas as pd
import numpy as np
from keras.preprocessing.image import ImageDataGenerator
from keras.models import load_model
from sklearn.metrics import classification_report
#from keras.utils.vis_utils import plot_model
from SDK.worker import worker
from SDK.const.const import wt

#传入文件的路径，返回路径，文件名字，文件后缀
def get_filePath_fileName_fileExt(filename):
    (filepath, tempfilename) = os.path.split(filename)
    (shotname, extension) = os.path.splitext(tempfilename)
    return filepath, shotname, extension

class mala_predict(worker):
    def __init__(self, workertype):
        #初始化一个dataset的worker
        worker.__init__(self, workertype)
        self.log.info("初始化一个训练的worker")

        self.BS = 100
        #totalTest_cross_domain = len(list(paths.list_images(config.TEST_PATH_CROSS_DOMAIN)))
        self.totalTest_cross_domain = 1
        self.log.info("totalTest_cross_domain=" + str(self.totalTest_cross_domain))

    def get_all_cells_list(self):
        #获得需要训练的分类
        types = self.projectinfo['types']
        self.totalTest_cross_domain = len(types)
        if len(types) < 2 and self.wtype == wt.TRAIN.value:
            self.log.error("less then 2 labels to train")
            return None
        #获得所有用作训练的细胞的信息
        df_allcells = None
        df_cells = pd.read_csv(self.cellslist_csv)
        for celltype in types:
            df2 = df_cells[df_cells['celltype'] == celltype]
            if df_allcells is None:
                df_allcells = df2
            else:
                df_allcells = df_allcells.append(df2)
        return df_allcells

    def _copy_train_cells(self, X, y, outdir):
        newX, newy = [], []
        for i in range(len(X)):
            cellpath_src, celltype = X[i], y[i]
            cells_type_dir = os.path.join(outdir, str(celltype))
            if not os.path.exists(cells_type_dir):
                os.makedirs(cells_type_dir)
            if not os.path.exists(cellpath_src):
                continue
            _, shotname, extension = get_filePath_fileName_fileExt(cellpath_src)
            cellpath_dst = os.path.join(cells_type_dir, shotname + extension)
            shutil.copyfile(cellpath_src, cellpath_dst)
            newX.append(cellpath_dst)
            newy.append(str(celltype))
        return newX, newy

    def copy_train_cells(self, df, test_size=0.2):
        X, y = [], []
        #拷贝训练数据到训练目录
        for index, imginfo in df.iterrows():
            cellpath_src = imginfo['cellpath']
            X.append(cellpath_src)
            y.append(str(imginfo['celltype']))

        if self.wtype == wt.PREDICT.value:
            newX, newy = self._copy_train_cells(X, y, self.project_predict_dir)
            return newX, None, newy, None
        elif self.wtype == wt.TRAIN.value:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
            newX_train, newy_train = self._copy_train_cells(X_train, y_train, self.project_train_dir)
            newX_test, newy_test = self._copy_train_cells(X_test, y_test, self.project_test_dir)
            return newX_train, newX_test, newy_train, newy_test
        return None, None, None, None

    def resize_img(self, X, y, outdir, outcsvpath, RESIZE=100):
        filelist = []
        for i in range(len(X)):
            cellpath, celltype = X[i], y[i]
            cellto_dir = os.path.join(outdir, celltype)
            if not os.path.exists(cellto_dir):
                os.makedirs(cellto_dir)
            img = cv2.imread(cellpath)
            if img.shape[0] != img.shape[1]:
                self.log.info("skip this image w != h: %s" % cellpath)
                continue
            img = cv2.resize(img, (RESIZE, RESIZE), interpolation=cv2.INTER_LINEAR)

            filepath, shotname, extension = get_filePath_fileName_fileExt(cellpath)
            cv2.imwrite(os.path.join(cellto_dir, shotname + extension), img)

            filelist.append([os.path.join(celltype, shotname + extension), celltype])

        if len(filelist) > 0:
            df = pd.DataFrame(filelist, columns=['File Name', 'Label'])
            df.to_csv(outcsvpath, quoting = 1, mode = 'w', index = False, header = True)
        return True

    def mkdatasets(self):
        size = self.projectinfo['parameter_resize']
        #获得所选数据集的细胞列表信息
        df = self.get_all_cells_list()
        if df is None or df.shape[0] < 1:
            return False
        #组织训练的目录结构
        if self.wtype == wt.PREDICT.value:
            X_predict, _, y_predict, _ = self.copy_train_cells(df)
            self.resize_img(X_predict, y_predict, self.project_resize_predict_dir, self.project_predict_labels_csv, RESIZE=size)
            return True
        elif self.wtype == wt.TRAIN.value:
            X_train, X_test, y_train, y_test = self.copy_train_cells(df)
            #resize
            self.resize_img(X_train, y_train, self.project_resize_train_dir, self.project_train_labels_csv, RESIZE=size)
            self.resize_img(X_test, y_test, self.project_resize_test_dir, self.project_test_labels_csv, RESIZE=size)
            return True

    def update_model_info_json(self, modinfo):
        if os.path.exists(self.info_json) is False:
            return False
        job_info = self.load_info_json()
        mod = modinfo

        mod['id'] = 0
        mod['type'] = 5
        mod['types'] = job_info['types']
        mod['pid'] = job_info['id']
        mod['path'] = self.project_mod_path
        mod['desc'] = '未保存的模型'
        mod['recall'] = -1
        mod['precision'] = mod['metric_value']

        with open(self.project_mod_json, 'w', encoding='utf-8') as file:
            file.write(json.dumps(mod, indent=2, ensure_ascii=False))
        return True

    def train_autokeras(self):
        time_limit = self.projectinfo['parameter_time']
        #Load images
        train_data, train_labels = load_image_dataset(csv_file_path=self.project_train_labels_csv,
                                                      images_path=self.project_resize_train_dir)
        test_data, test_labels = load_image_dataset(csv_file_path=self.project_test_labels_csv,
                                                    images_path=self.project_resize_test_dir)

        train_data = train_data.astype('float32') / 255
        test_data = test_data.astype('float32') / 255
        self.log.info("Train data shape: %d" % train_data.shape[0])

        clf = ImageClassifier(verbose=True, path=self.project_tmp_dir, resume=False)
        clf.fit(train_data, train_labels, time_limit=time_limit)
        clf.final_fit(train_data, train_labels, test_data, test_labels, retrain=True)

        evaluate_value = clf.evaluate(test_data, test_labels)
        self.log.info("Evaluate: %f" % evaluate_value)

        clf.export_autokeras_model(self.project_mod_path)

        #统计训练信息
        dic = {}
        ishape = clf.cnn.searcher.input_shape
        dic['n_train'] = train_data.shape[0]  #训练总共用了多少图
        dic['n_classes'] = clf.cnn.searcher.n_classes
        dic['input_shape'] = str(ishape[0]) + 'x' + str(ishape[1]) + 'x' + str(ishape[2])
        dic['history'] = clf.cnn.searcher.history
        dic['model_count'] = clf.cnn.searcher.model_count
        dic['best_model'] = clf.cnn.searcher.get_best_model_id()
        best_model = [item for item in dic['history'] if item['model_id'] == dic['best_model']]
        if len(best_model) > 0:
            dic['loss'] = best_model[0]['loss']
            dic['metric_value'] = best_model[0]['metric_value']
        dic['evaluate_value'] = evaluate_value
        return dic

    def predict(self):
        ret = self.mkdatasets()
        if ret is False:
            return False

        # initialize the testing generator for cross domain
        valAug = ImageDataGenerator(rescale=1 / 255.0)
        testGen_cross_domain = valAug.flow_from_directory(
                self.project_resize_predict_dir,
        	class_mode="categorical",
        	target_size=(64, 64),
        	color_mode="rgb",
        	shuffle=False,
        	batch_size=self.BS)

        model=load_model("mala.h5")
        # 保存模型结构图
        #plot_model(model, to_file='model1.png',show_shapes=True)
        # reset the testGen_cross_domain generator and then use our trained model to
        # make predictions on the data
        print("[INFO] evaluating network ...(testGen_cross_domain)")
        testGen_cross_domain.reset()
        predIdxs = model.predict_generator(testGen_cross_domain,
        	steps=(self.totalTest_cross_domain // self.BS+1),verbose=1)

        classes = list(np.argmax(predIdxs, axis=1))
        filenames = testGen_cross_domain.filenames
        print(testGen_cross_domain.classes)
        for f in zip(filenames, testGen_cross_domain.classes, classes):
           print (f)

        # for each image in the testing set we need to find the index of the
        # label with corresponding largest predicted probability
        #predIdxs = np.argmax(predIdxs, axis=1)

        ## show a nicely formatted classification report
        #print('\n',classification_report(testGen_cross_domain.classes, predIdxs,
        #	target_names=testGen_cross_domain.class_indices.keys()))

        #df_result = pd.DataFrame(result, columns=['cellpath', 'true_label', 'predict_label', 'correct'])
        return True

def worker_load(w):
    w_str = "训练" if w.wtype == wt.TRAIN.value else "预测"

    wid, wdir = w.get_job()
    if wdir == None:
        return
    w.log.info("获得一个%s任务%d 工作目录%s" % (w_str, wid, wdir))

    ret = True
    w.prepare(wid, wdir, w.wtype)
    w.log.info("初始化%s文件目录完成" % w_str)

    w.projectinfo = w.load_info_json()
    w.log.info("读取%s信息完成" % w_str)

    w.log.info("开始%s" % w_str)
    w.woker_percent(4, 1800)
    if w.wtype == wt.TRAIN.value:
        ret = w.train()
    elif w.wtype == wt.PREDICT.value:
        ret = w.predict()

    if ret == True:
        w.done()
        w.log.info("%s完成 %d 工作目录%s" % (w_str, wid, wdir))
    else:
        w.error()
        w.log.warning("%s出错 %d 工作目录%s" % (w_str, wid, wdir))
    return

if __name__ == '__main__':
    w = mala_predict(wt.PREDICT.value)
    while 1:
        worker_load(w)
        time.sleep(10)

