import torch
import torch.nn as nn
import glob
import os
import sys
import numpy as np 
import random
import matplotlib.pyplot as plt
from PIL import Image
from torchvision import transforms
from torch.utils.tensorboard.writer import SummaryWriter
from more_itertools import unzip


def get_cosine_similarity(a, b):
  a_norm = a / a.norm(dim=1)[:, None]
  b_norm = b / b.norm(dim=1)[:, None]
  res = torch.mm(a_norm, b_norm.transpose(0,1))
  
  return res

def get_Euclidean_dist(a, b):
  res = torch.cdist(a, b, p=2)
  return res

def get_Euclidean_similarity(a, b):
  res = 1/1+torch.cdist(a, b, p=2)
  return res

def get_dot_prod_similarity(a,b):
  return np.dot(a,b.T)

def sharpening_softabs(x,beta=10):
  return 1/(1+torch.exp(-beta*(x-0.5)))+1/(1+torch.exp(-beta*(-x-0.5)))

def sharpening_softmax(x):
  res = torch.nn.functional.softmax(x)
  return res

def normalize(x):
  return x/torch.sum(x,axis=1).reshape(-1,1)

def weighted_sum(attention_vec, value_mem):
  return torch.mm(attention_vec,value_mem)

def binarize(keys):
  return np.where(keys>0, 1, 0)

def bipolarize(keys):
  return np.where(keys>0, 1, -1)

def image_file_to_array(filename, transform):
  image = Image.open(filename)
  image = transform(image)
  arr = np.asarray(image)
  return 1.0 - arr.astype(np.float32)

def prep_data(batch_labels, batch_imgs, device):
  B,H,W = batch_imgs.shape
  batch_imgs = batch_imgs.reshape((B,1,H,W))
  inputs = torch.tensor(batch_imgs).float().to(device)
  targets = torch.tensor(batch_labels).float().to(device)
  return targets, inputs

def quantize(x, num_bits=0):
    if num_bits == 0:
        q_x = x
    else:
        qmin = 0.
        qmax = 2.**num_bits - 1.
        min_val, max_val = x.min(), x.max()

        #print(qmax, qmin,num_bits)
        scale = (max_val - min_val) / (qmax - qmin)
        if scale != 0:
            initial_zero_point = 0
            scale = 1.0        
        else:    
            initial_zero_point = qmin - min_val / scale
        zero_point = 0.0

        if initial_zero_point < qmin:
            zero_point = qmin
        elif initial_zero_point > qmax:
            zero_point = qmax
        elif scale == 0:
            zero_point = 0.0        
        else:
            zero_point = initial_zero_point

        zero_point = int(zero_point)
        q_x = (zero_point + x)*qmax 
        q_x = q_x.clamp(qmin, qmax).round()
        #print(q_x)
    
    return q_x

def normal_dist_variation(x, n_bits, var=0):
  scale = var * 2**n_bits
  normal_dist = torch.randn(x.shape[0], x.shape[1]) * scale
  return normal_dist