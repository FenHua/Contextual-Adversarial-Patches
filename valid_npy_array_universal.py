from darknet import Darknet
import dataset_eval_npy_array_universal
import torch
from torch.autograd import Variable
from torchvision import datasets, transforms
from utils import *
import os

use_cuda = True
gpus = sys.argv[8]
if use_cuda:
	os.environ['CUDA_VISIBLE_DEVICES'] = gpus


def valid(datacfg, cfgfile, weightfile, outfile, valid_images):
	options = read_data_cfg(datacfg)
	name_list = options['names']

	classname = sys.argv[5]
	noise_path = sys.argv[6]
	result_prefix = sys.argv[7]
	prefix = result_prefix
	names = load_class_names(name_list)

	with open(valid_images) as fp:
		tmp_files = fp.readlines()
		valid_files = [item.rstrip() for item in tmp_files]

	m = Darknet(cfgfile)
	m.print_network()
	m.load_weights(weightfile)
	m.cuda()
	m.eval()

	valid_dataset = dataset_eval_npy_array_universal.listDataset(valid_images, shape=(m.width, m.height),
					   shuffle=False,
					   transform=None,               # already returning tensor
					   noise_path=noise_path)
	valid_batchsize = 2
	assert(valid_batchsize > 1)

	kwargs = {'num_workers': 4, 'pin_memory': True}
	valid_loader = torch.utils.data.DataLoader(
		valid_dataset, batch_size=valid_batchsize, shuffle=False, **kwargs)

	fps = [0]*m.num_classes
	if not os.path.exists(result_prefix):
		os.makedirs(result_prefix)

	# print('results/no_class_overlap/' + classname)
	for i in range(m.num_classes):
		buf = '%s/%s%s.txt' % (prefix, outfile, names[i])
		fps[i] = open(buf, 'w')

	lineId = -1

	conf_thresh = 0.005
	nms_thresh = 0.45
	for batch_idx, (data, target, dummy) in enumerate(valid_loader):  # Changed by Aniruddha
		data = data.cuda()
		data = Variable(data, volatile = True)
		output = m(data).data
		batch_boxes = get_region_boxes(output, conf_thresh, m.num_classes, m.anchors, m.num_anchors, 0, 1)
		for i in range(output.size(0)):
			lineId = lineId + 1
			fileId = os.path.basename(valid_files[lineId]).split('.')[0]
			width, height = get_image_size(valid_files[lineId])
			print(valid_files[lineId])
			boxes = batch_boxes[i]
			boxes = nms(boxes, nms_thresh)
			for box in boxes:
				x1 = (box[0] - box[2]/2.0) * width
				y1 = (box[1] - box[3]/2.0) * height
				x2 = (box[0] + box[2]/2.0) * width
				y2 = (box[1] + box[3]/2.0) * height

				det_conf = box[4]
				for j in range((len(box)-5)/2):
					cls_conf = box[5+2*j]
					cls_id = box[6+2*j]
					prob =det_conf * cls_conf
					fps[cls_id].write('%s %f %f %f %f %f\n' % (fileId, prob, x1, y1, x2, y2))

	for i in range(m.num_classes):
		fps[i].close()

if __name__ == '__main__':
	import sys
	if len(sys.argv) == 9:
		datacfg = sys.argv[1]
		cfgfile = sys.argv[2]
		weightfile = sys.argv[3]
		outfile = 'comp4_det_test_'
		valid_images = sys.argv[4]
		valid(datacfg, cfgfile, weightfile, outfile, valid_images)
	else:
		print('Usage:')
		print(' python valid_npy_array_universal_hamed1.py datacfg cfgfile weightfile valid_images classname noise_path result_prefix gpu')
