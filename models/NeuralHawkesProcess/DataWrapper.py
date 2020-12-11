# -*- coding: utf-8 -*-
"""DataWrapper.ipynb
Automatically generated by Colaboratory.
Original file is located at
    https://colab.research.google.com/drive/15YYfs_DCyUp_SyK2vJpqWnPB3Czw2LAJ
"""

import torch
from torch.utils.data import Dataset
import pickle

class NHPDataset(Dataset):
    ''' 
    Create Dataset for Neural Hawkey Process
    using financial data from original paper
    '''

    def __init__(self, file_path):
        self.event_type = []
        self.event_time = []

        with open(file_path, 'rb') as f:

            if 'dev' in file_path:
                seqs = pickle.load(f, encoding='latin1')['dev']
            elif 'train' in file_path:
                seqs = pickle.load(f, encoding='latin1')['train']
            elif 'test' in file_path:
                seqs = pickle.load(f, encoding='latin1')['test']

            for idx, seq in enumerate(seqs):
                self.event_type.append(torch.Tensor([int(event['type_event']) for event in seq]))
                self.event_time.append(torch.Tensor([float(event['time_since_start']) for event in seq]))

    def __len__(self):
        return len(self.event_type)
    
    def __getitem__(self, index):

        event_type = torch.LongTensor(self.event_type[index].long())[1:]
        event_time = torch.Tensor(self.event_time[index])
        #delta_time = torch.zeros_like(event_time)
        delta_time = event_time[1:] - event_time[:-1]
        
        return delta_time, event_type

def collate_fn(batch, n_events=2):

      """
      While initializing LSTM we have it read a special beginning-of-stream (BOS) event (k0, t0), 
      where k0 is a special event type and t0 is set to be 0 
      (expanding the LSTM’s input dimensionality by one) see Appendix A.2
      Input:
          batch tuple((batch_size, seq_len)x2) - batch with event types sequence and corresponding inter-arrival times
      Output:
          pad_event_seq (batch_size, seq_len) - padded event types sequence
          pad_time_seq (batch_size, seq_len) - padded event times sequence
      """
      seq_time = torch.stack([sample[0] for sample in batch])
      seq_events = torch.stack([sample[1] for sample in batch])

      pad_event = torch.zeros_like(seq_events[:,0]) + n_events
      pad_time = torch.zeros_like(seq_time[:,0])
      pad_event_seq = torch.cat((pad_event.reshape(-1,1), seq_events), dim=1)
      pad_time_seq = torch.cat((pad_time.reshape(-1,1), seq_time), dim=1)

      return pad_event_seq.long(), pad_time_seq
