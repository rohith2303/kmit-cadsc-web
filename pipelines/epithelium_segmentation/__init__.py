import numpy as np
from PIL import Image
import cv2
from .model import build_model
import os
import matplotlib.pyplot as plt

INPUT_SHAPE = (960, 960, 3)
WEIGHTS_PATH = './pipelines/epithelium_segmentation/weights/model.h5'

def preprocess(x):
    x = cv2.resize(x, INPUT_SHAPE[:2])
    return x

def run_model(x):
    model = build_model(INPUT_SHAPE)
    model.load_weights(WEIGHTS_PATH)
    x = x.reshape(1, *INPUT_SHAPE).astype(np.float64)
    pred = model.predict(x)
    return pred

def postprocess(orig, pred):
    pred[np.where(pred<=0.5)] = 0
    pred[np.where(pred>0.5)] = 1
    pred = (pred.reshape(INPUT_SHAPE[:2])*255).astype(np.uint8)
    pred = cv2.dilate(pred, np.ones((3,3),np.uint8), iterations=1)
    pred = removeSmallConnectedComponents(pred, min_size=300)
    pred = remove_white(orig, pred)
    pred = overlay_mask_boundaries(orig, pred)
    return pred

def postprocessing(orig, im):
    if im.shape[-1] == 1:
        im = im.reshape(im.shape[:-1])
    return im

def get_display_image(fname):
    inp = np.array(Image.open(fname))
    preprocessed = preprocess(inp)
    pred = run_model(preprocessed)
    postprocessed = postprocess(preprocessed, pred)
    #print(postprocessed)
    #plt.imshow(postprocessed)
    #plt.show()

def removeSmallConnectedComponents(img, min_size=50):
    if img.shape[-1] == 1:
        img = (img.reshape(*img.shape, 1)*255).astype(np.uint8)
    else:
        img = (img.reshape(*img.shape, 1)*255).astype(np.uint8)
    nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(img, connectivity=8)
    sizes = stats[1:, -1]; nb_components = nb_components - 1
    img2 = np.zeros((output.shape))
    for i in range(0, nb_components):
        if sizes[i] >= min_size:
            img2[output == i + 1] = 1
    return img2

#removes white stroma regions in the original image, from the mask image
def remove_white(orig, mask):
    orig = orig.astype(np.uint8)
    if orig.shape[-1] != 1:
        orig = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    orig = (orig*255).astype(np.uint8)
    ret,th = cv2.threshold(orig,100,255,cv2.THRESH_BINARY)
    if mask.shape[-1] == 1:
        mask = mask.reshape(mask.shape[:-1])
    mask = mask*(th==255)
    return mask

#overlays mask's boundaries over original image
def overlay_mask_boundaries(orig, mask):
    for_boundary = (mask*255).astype(np.uint8)
    for i in range(1):
        for_boundary = cv2.medianBlur(for_boundary, 5)
    for_boundary = cv2.morphologyEx(for_boundary, cv2.MORPH_CLOSE, np.ones((5,5),np.uint8), iterations=2)
    for_boundary[:2,:] = 0
    for_boundary[-2:,:] = 0
    for_boundary[:,:2] = 0
    for_boundary[:,-2:] = 0
    _, contours, hierarchy = cv2.findContours(for_boundary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    boundary_image = orig.copy()
    cv2.drawContours(boundary_image, contours, -1, (0, 255, 0), 4)
    return boundary_image