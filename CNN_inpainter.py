# -*- coding: utf-8 -*-

import torch
import torchvision
from torch import nn
from torch.autograd import Variable
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.utils import save_image
from torchvision.datasets import STL10, ImageFolder
import os, sys
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

if sys.version_info >= (3, 0, 0):
    import urllib.request as urllib
else:
    import urllib
try:
    from imageio import imsave
except:
    from scipy.misc import imsave

if not os.path.exists('./model_output'):
    os.mkdir('./model_output')

if not os.path.exists('./img_mask'):
    os.mkdir('./img_mask')

if not os.path.exists('./img_mask/mask'):
    os.mkdir('./img_mask/mask')

if not os.path.exists('./img_org'):
    os.mkdir('./img_org')

if not os.path.exists('./img_org/org'):
    os.mkdir('./img_org/org')


def read_and_convert(path, out, opt):

    with open(path, 'rb') as f:
        # read whole file in uint8 chunks
        everything = np.fromfile(f, dtype=np.uint8)
        images = np.reshape(everything, (-1, 3, 96, 96))
        # Now transpose the images into a standard image format
        # readable by, for example, matplotlib.imshow
        images = np.transpose(images, (0, 3, 2 ,1))

        if opt == 'y':
        #Mask that cuts out a shape on the images
          images[:, 10:16, 10:25, :] = 0

    i = 0
    for image in images:
      imsave("./img_{0}/{0}/{1}s.png".format(out,out+str(i)), image, format="png")
      i = i + 1

def to_img(x):
    x = 0.5 * (x + 1)
    x = x.clamp(0, 1)
    x = x.view(x.size(0), 3, 96, 96)
    return x

#Setup
num_epochs =100
batch_size = 5
learning_rate = 1e-3
train_bin = './data/stl10_binary/train_X.bin'
test_bin = './data/stl10_binary/test_X.bin'

img_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,0.5,0.5), (0.5,0.5,0.5))])

#Loading of the original STL10 images - dowloading them from the Standford servers.
STL10('./data', split='train', transform=img_transform, download=True)
#data_load = DataLoader(data_set, batch_size=batch_size, shuffle=False)

#Loading of the STL10 binaries that are goin to be masked
read_and_convert(train_bin, out='mask', opt='y')
read_and_convert(train_bin, out='org', opt=None)


#Loading the original pictures
data_set = ImageFolder(root='/content/img_org', transform=img_transform)
data_org = DataLoader(data_set, batch_size=batch_size, shuffle=False)

#Loading of the masked STL10 png
data_setmask = ImageFolder(root='/content/img_mask', transform=img_transform)
data_mask = DataLoader(data_setmask, batch_size=batch_size, shuffle=False)


#print(data_setmask[15])
#print(5*'###############################\n')
#print(data_set[15])


class inpaintencode(nn.Module):
    def __init__(self):
        super(inpaintencode, self).__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 64, 3, stride=3, padding=1),
            nn.ReLU(True),
            nn.MaxPool2d(2, stride=2),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.ReLU(True),
            nn.MaxPool2d(2, stride=1)
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(128, 64, 3, stride=2),
            nn.ReLU(True),
            nn.ConvTranspose2d(64, 32, 5, stride=3, padding=1),
            nn.ReLU(True),
            nn.ConvTranspose2d(32, 3, 10, stride=2, padding=1),
            nn.Tanh()
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x


model = inpaintencode().cuda()
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate,
                             weight_decay=1e-5)

for epoch in range(num_epochs):
    for it, (data1, data2) in enumerate(zip(data_org, data_mask)):
        img, _ = data1
        img_mask, _ = data2

        img = Variable(img).cuda()
        img_mask = Variable(img_mask).cuda()
          
        #forward
        output = model(img_mask)
        loss = criterion(output, img)
        #backpropagation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
    #progress printing
    print('epoch [{}/{}], loss:{:.4f}'
          .format(epoch+1, num_epochs, loss.data.item()))
    if epoch % 10 == 0:
        pic = to_img(output.cpu().data)
        pic_org = to_img(img_mask.cpu().data)

        pic_org[:,:,10:16, 10:25] = pic[:,:,10:16, 10:25]

        save_image(pic, './model_output/image_{}.png'.format(epoch))

        save_image(pic_org, './model_output/Orgimage_{}.png'.format(epoch))

torch.save(model.state_dict(), './conv_autoencoder.pth')
