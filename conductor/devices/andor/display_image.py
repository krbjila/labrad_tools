import numpy as np
from matplotlib import pyplot as plt
from sys import argv

# if there is an argument, use that as the path to the image
if len(argv) > 1:
    path = argv[1]
else:
    path = "/home/bialkali/labrad_tools/conductor/poo.npz"
data = np.load(path)["arr_0"]

# (frame, FK frame, y, x)
# show subplots of each frame and FK frame with titles saying the max pixel value
frames, fkframes, y, x = data.shape
fig, axes = plt.subplots(frames, fkframes, figsize=(10, 10))
for i in range(frames):
    for j in range(fkframes):
        if frames > 1:
            axes[i, j].imshow(data[i, j, :, :], cmap="gray")
            axes[i, j].set_title("Max pixel value: {}".format(np.max(data[i, j, :, :])))
        else:
            axes[j].imshow(data[i, j, :, :], cmap="gray")
            axes[j].set_title("Max pixel value: {}".format(np.max(data[i, j, :, :])))
plt.show()