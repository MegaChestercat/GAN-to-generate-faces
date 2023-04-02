# -*- coding: utf-8 -*-
"""gan_that_generates_faces.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1FqcSWNIfY8EBVmywAovB9H3mWsPDKxm_

# GAN that generates faces

The objective of this Jupyter Notebook is the creation of a GAN (Generative Adversarial Network) that has the capability of creating faces, based on the "celeb" dataset.

## Requirements

* Python 3
* Tensorflow
* GPU (so the training process can be faster)
* Google Drive Account
* Celeb dataset

🚨 Have activated **Hardware Acceleration** with GPU
"""

!nvidia-smi -L

"""## Step 1. Mount Google Drive"""

# Commented out IPython magic to ensure Python compatibility.
from google.colab import drive
drive.mount('/gdrive', force_remount=True)
# %cd /gdrive

"""## Step 2. Install needed libraries"""

!pip install imageio
!pip install git+https://github.com/tensorflow/docs
!pip install tensorflow==2.7

import tensorflow as tf

print(tf.__version__)

"""## Step 3. Importing libraries"""

import tensorflow as tf
from tensorflow.keras.layers import Input, Reshape, Dropout, Dense, Flatten, BatchNormalization, Activation, ZeroPadding2D, LeakyReLU, UpSampling2D, Conv2D
from tensorflow.keras.models import Sequential, Model, load_model
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.initializers import RandomNormal
from tensorflow.keras.optimizers import Adam
import numpy as np
import os
import time
from tqdm import tqdm
import matplotlib.pyplot as plt
from PIL import Image
import glob
import imageio

"""## Step 4. Initial Variables & Loading Images into dataset """

RES_FACTOR = 4
IMAGE_RES = 32 * RES_FACTOR
IMAGES_PATH = "MyDrive/GAN/src/face_images/"
DATA_PATH = "MyDrive/GAN/src"
CHECKPOINT_PATH = "MyDrive/GAN/src/output/checkpoints"
EPOCH_NUM = 1000
BATCH_SIZE = 35
COLOR_MODE = "rgb" #The options are "grayscale" (1 channel), "rgb" (3 channels), & "rgba" (4 channels)
IMAGE_CHANNELS = 3 #This variable means the same as the COLOR_MODE variable but is for specific statements where a number is required
SEED_SIZE = 100 #Range until where the size of the seed vector can use
CURRENT_EPOCH = 1
SAVE_EVERY_N_EPOCH = 50
# Preview image data
PREVIEW_ROWS = 4
PREVIEW_COLS = 7
PREVIEW_MARGIN = 16

print(f"The GAN will generate {IMAGE_RES}px square images.")

dataset = tf.keras.utils.image_dataset_from_directory(
    IMAGES_PATH, label_mode = None, color_mode = COLOR_MODE, batch_size = BATCH_SIZE, image_size = (IMAGE_RES, IMAGE_RES), crop_to_aspect_ratio = True, shuffle = True
)

dataset = dataset.map(lambda x: x / 255.0)

for i in dataset:
    plt.axis("off")
    plt.imshow((i.numpy() * 255).astype("int32")[0])
    break

"""# Step 5. Generator & Discriminator Definition"""

def Discriminator(image_shape):
    
    model = Sequential()
    
    model.add(Conv2D(32, strides = 2, kernel_size = 4, input_shape= image_shape, padding = "same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
    model.add(BatchNormalization(momentum=0.99))
    model.add(LeakyReLU(alpha = 0.2))
    
    model.add(Dropout(0.25))
    model.add(Conv2D(64, strides = 2, kernel_size = 4, padding="same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
    model.add(ZeroPadding2D(padding=((0,1),(0,1))))
    model.add(BatchNormalization(momentum=0.99))
    model.add(LeakyReLU(alpha = 0.2))

    model.add(Dropout(0.25))
    model.add(Conv2D(128, strides = 2, kernel_size = 4, padding="same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
    model.add(ZeroPadding2D(padding=((0,1),(0,1))))
    model.add(BatchNormalization(momentum=0.99))
    model.add(LeakyReLU(alpha = 0.2))
    
    model.add(Dropout(0.25))
    model.add(Conv2D(256, strides = 1, kernel_size = 4, padding="same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
    model.add(BatchNormalization(momentum=0.99))
    model.add(LeakyReLU(alpha = 0.2))

    model.add(Dropout(0.25))
    model.add(Conv2D(512, strides = 1, kernel_size = 4, padding="same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
    model.add(BatchNormalization(momentum=0.99))
    model.add(LeakyReLU(alpha = 0.2))
    
    model.add(Dropout(0.25))
    model.add(Flatten())
    model.add(Dense(1, activation = 'sigmoid'))
    
    return model


def Generator(seed_size, channels):
    
    model = Sequential()
    model.add(Dense(4 * 4 * 256, input_dim = seed_size))
    model.add(Reshape((4,4,256)))
    
    model.add(UpSampling2D())
    model.add(Conv2D(256, strides = 1, kernel_size = 4, padding="same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
    model.add(BatchNormalization(momentum=0.99))
    model.add(LeakyReLU(alpha = 0.2))

    model.add(UpSampling2D())
    model.add(Conv2D(256, strides = 1, kernel_size = 4, padding="same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
    model.add(BatchNormalization(momentum=0.99))
    model.add(LeakyReLU(alpha = 0.2))

    model.add(UpSampling2D())
    model.add(Conv2D(128, strides = 1, kernel_size = 4, padding="same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
    model.add(BatchNormalization(momentum=0.99))
    model.add(LeakyReLU(alpha = 0.2))

    if RES_FACTOR > 1:
      model.add(UpSampling2D(size=(RES_FACTOR,RES_FACTOR)))
      model.add(Conv2D(128, strides = 1, kernel_size = 4, padding="same", kernel_initializer=RandomNormal(mean=0.0, stddev=0.02)))
      model.add(BatchNormalization(momentum=0.99))
      model.add(LeakyReLU(alpha = 0.2))
    
    
    model.add(Conv2D(channels, strides = 1, kernel_size = 5, padding="same", activation = "sigmoid"))
    
    return model

"""## Step 6. Save Images Method Definition"""

def save_images(cnt,noise):
    image_array = np.full((
    PREVIEW_MARGIN + (PREVIEW_ROWS * (IMAGE_RES+PREVIEW_MARGIN)), 
    PREVIEW_MARGIN + (PREVIEW_COLS * (IMAGE_RES+PREVIEW_MARGIN)), IMAGE_CHANNELS), 
    255, dtype=np.uint8)
    
    generated_images = generator.predict(noise)
    generated_images = 0.5 * generated_images + 0.5
    
    image_count = 0
    for row in range(PREVIEW_ROWS):
        for col in range(PREVIEW_COLS):
            r = row * (IMAGE_RES+16) + PREVIEW_MARGIN
            c = col * (IMAGE_RES+16) + PREVIEW_MARGIN
            image_array[r:r+IMAGE_RES,c:c+IMAGE_RES] \
                = generated_images[image_count] * 255
            image_count += 1
    
    output_path = os.path.join(DATA_PATH,'output')
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        
    filename = os.path.join(output_path,f"image_at_epoch_{cnt}.png")
    im = Image.fromarray(image_array)
    im.save(filename)

"""## Step 7. Testing the generator and Discriminator functions"""

generator = Generator(SEED_SIZE, IMAGE_CHANNELS)
generator.summary()
noise = tf.random.normal([1, SEED_SIZE])
generated_image = generator(noise, training=False)

plt.imshow(generated_image[0, :, :, 0])

image_shape = (IMAGE_RES,IMAGE_RES,IMAGE_CHANNELS)

discriminator = Discriminator(image_shape)
discriminator.summary()
decision = discriminator(generated_image)
print (decision)

"""## Step 8. Defining the loss function (Cross-Entropy) and Optimizer(Adam)"""

cross_entropy = tf.keras.losses.BinaryCrossentropy()

def discriminator_loss(real_output, fake_output):
    real_loss = cross_entropy(tf.ones_like(real_output), real_output)
    fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
    total_loss = real_loss + fake_loss
    return total_loss

def generator_loss(fake_output):
    return cross_entropy(tf.ones_like(fake_output), fake_output)

generator_optimizer = tf.keras.optimizers.Adam(learning_rate=0.0001,beta_1=0.5, clipvalue=1.0, decay=1e-8)
discriminator_optimizer = tf.keras.optimizers.Adam(learning_rate=0.0001,beta_1=0.5, clipvalue=1.0, decay=1e-8)

"""## Step 8.5 Adding Checkpoint System and a fixed seed



"""

checkpoint = tf.train.Checkpoint(generator_optimizer=generator_optimizer,
                          discriminator_optimizer=discriminator_optimizer,
                          generator=generator,
                          discriminator=discriminator)

manager = tf.train.CheckpointManager(checkpoint, CHECKPOINT_PATH, max_to_keep=3)

fixed_seed = np.random.normal(0, 1, (PREVIEW_ROWS * PREVIEW_COLS, 
                                       SEED_SIZE))

"""## Step 9. Generator and Discriminator Training Definition"""

@tf.function
def train_step(images):
    seed = tf.random.normal([BATCH_SIZE, SEED_SIZE])

    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
        generated_images = generator(seed, training=True)

        real_output = discriminator(images, training=True)
        fake_output = discriminator(generated_images, training=True)

        gen_loss = generator_loss(fake_output)
        disc_loss = discriminator_loss(real_output, fake_output)
    

        gradients_of_generator = gen_tape.gradient(\
            gen_loss, generator.trainable_variables)
        gradients_of_discriminator = disc_tape.gradient(\
            disc_loss, discriminator.trainable_variables)

        generator_optimizer.apply_gradients(zip(
            gradients_of_generator, generator.trainable_variables))
        discriminator_optimizer.apply_gradients(zip(
            gradients_of_discriminator, 
            discriminator.trainable_variables))
    return gen_loss,disc_loss

def hms_string(sec_elapsed):
    h = int(sec_elapsed / (60 * 60))
    m = int((sec_elapsed % (60 * 60)) / 60)
    s = sec_elapsed % 60
    return "{}:{:>02}:{:>05.2f}".format(h, m, s)

def train(dataset, epochs):
    if manager.latest_checkpoint:
        checkpoint.restore(manager.latest_checkpoint)
        latest_epoch = int(manager.latest_checkpoint.split('-')[1])
        CURRENT_EPOCH = latest_epoch * SAVE_EVERY_N_EPOCH
        print("Latest checkpoint of epoch {} restored".format(CURRENT_EPOCH))
    else:
        print("Initializing from scratch.")
        CURRENT_EPOCH = 1
      
    start = time.time()

    for epoch in range(CURRENT_EPOCH, epochs+1):
        epoch_start = time.time()

        gen_loss_list = []
        disc_loss_list = []

        for image_batch in dataset:
            t = train_step(image_batch)
            gen_loss_list.append(t[0]) 
            disc_loss_list.append(t[1])

        g_loss = sum(gen_loss_list) / len(gen_loss_list)
        d_loss = sum(disc_loss_list) / len(disc_loss_list)
        
        save_images(epoch,fixed_seed)
          
        if epoch % SAVE_EVERY_N_EPOCH == 0:
          manager.save()
          epoch_elapsed = time.time()-epoch_start
          print (f'Saved Epoch {epoch}, gen loss={g_loss},disc loss={d_loss},'\
               f' {hms_string(epoch_elapsed)}')
          
        if epoch == epochs:
           manager.save()
           epoch_elapsed = time.time()-epoch_start
           print (f'Saved Final Epoch {epoch}, gen loss={g_loss},disc loss={d_loss},'\
               f' {hms_string(epoch_elapsed)}')
        
        epoch_elapsed = time.time()-epoch_start
        print (f'Epoch {epoch}, gen loss={g_loss},disc loss={d_loss},'\
               f' {hms_string(epoch_elapsed)}')

    elapsed = time.time()-start
    print (f'Training time: {hms_string(elapsed)}')

"""## Step 10. Start the training """

train(dataset, EPOCH_NUM)

"""## Step 11. Save the Generator and Discriminator models after training"""

generator.save(os.path.join(DATA_PATH,"face_generator.h5"))
discriminator.save(os.path.join(DATA_PATH,"face_discriminator.h5"))

"""## Step 12. Create a GIF file of all the generated images (optional)"""

# Commented out IPython magic to ensure Python compatibility.
# %cd ..

anim_file = 'dcgan.gif'

with imageio.get_writer(anim_file, mode='I') as writer:
  filenames = glob.glob("gdrive/MyDrive/GAN/src/output/image*.png")
  filenames = sorted(filenames)
  for filename in filenames:
    image = imageio.imread(filename)
    writer.append_data(image)

import tensorflow_docs.vis.embed as embed
embed.embed_file(anim_file)