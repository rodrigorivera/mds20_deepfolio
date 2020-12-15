# -*- coding: utf-8 -*-
"""model.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1HpDrYfebGHN4EVJl-Z_GDTZ9npmrKhAd
"""

import torch
import torch.nn as nn
from torch.nn import functional as F
from torch import optim

import numpy as np

def create_unifrom_d(event_times, device = None):
  
    """
    Create uniform distribution of t from given event sequenses
    Input:
        event_times (batch_size, seq_len) - inter-arrival times of events
    Output:
        sim_inter_times (batch_size, seq_len) - simulated inter-arrival times of events
    """

    batch_size, batch_len = event_times.shape
    sim_inter_times = []
    tot_time_seqs = event_times.sum(dim=1)
    for tot_time in tot_time_seqs:

          # create t ∼ Unif(0, T)
          sim_time_seqs = torch.sort(torch.zeros(batch_len).uniform_(0,tot_time)).values

          # calc inter-arrival times
          sim_inter_time = torch.zeros(batch_len)
          sim_inter_time[1:] = sim_time_seqs[1:] - sim_time_seqs[:-1]
          sim_inter_times.append(sim_inter_time)

    sim_inter_times = torch.stack(sim_inter_times)
    return sim_inter_times.to(device) if device != None else sim_inter_times

class UNIPoint(nn.Module):
    def __init__(self, n_features, n_parameters, n_basis_functions, device, hidden_size=256):
      """
      Input parameters:
      n_neurons - number of neurons inside RNN
      n_parameters - expecteed number of parameters in basis function
      n_basis_functions - number of basis functions
      """
      super(UNIPoint, self).__init__()

      #self.rnn = nn.RNNCell(n_features, hidden_size) # uncomment if RNN
      self.rnn = nn.LSTMCell(n_features, hidden_size) # uncomment if LSTM
      self.h2p = nn.Linear(hidden_size, n_parameters * n_basis_functions)
      self.Softplus = torch.nn.Softplus(beta = 1)

      self.n_basis_functions = n_basis_functions
      self.hidden_size = hidden_size
      self.device = device

      self.time_predictor  = nn.Linear(hidden_size, 1, bias=False) #here 12 is a batch_size - fix later

    def ReLU(self, parameter_1, parameter_2, time):
      """Function to apply Rectified Linear Unit (ReLU) as basis function inside network 
        Input parameters:
          parameters - alpha, beta for basis function's value calculation
          time - column-vector with interarrival time between events of temporal point process (TPP)
      """
      self.output = torch.relu(self.parameters[:,parameter_1] * time + self.parameters[:,parameter_2] ) 
      return self.output
    
    def PowerLaw(self, parameter_1, parameter_2, time): 
      """Function to apply Power Law (PL) as basis function inside network 
        Input parameters:
          parameters - alpha, beta for basis function's value calculation
          time - column-vector with interarrival time between events of temporal point process (TPP)
      """
      self.output = self.parameters[:,parameter_1] * (1 + time)**( - self.parameters[:,parameter_2])
      return self.output

    def Exponential(self, parameter_1, parameter_2, time): 
      """Function to apply Exponential function as basis function inside network 
        Input parameters:
          parameters - alpha, beta for basis function's value calculation
          time - column-vector with interarrival time between events of temporal point process (TPP)
      """
      self.output = self.parameters[:,parameter_1] * torch.exp(self.parameters[:, parameter_2] * time)
      return self.output


    def intensity_layer(self, tau):
          '''
          Layer to calculate intesity with respect to time from the last event

          Input: tau - time from the last event
          '''

          for function in range(self.n_basis_functions): 
              # calculating numbers of parameters to take for basis function
              par1 = 2 * function
              par2 = 2 * function + 1  
              self.basis_res[:, function] = self.PowerLaw(par1, par2, tau) 
                            
          self.sum_res = torch.sum(self.basis_res, 1)
          intensity = self.Softplus(self.sum_res) * 0.0000001

          return intensity

    def init_hidden(self, batch_size, hidden_size):

      self.hx = torch.randn(batch_size, hidden_size, device=self.device) # initialize hidden state 
      self.basis_res = torch.randn(batch_size, self.n_basis_functions) #initialize matrix for basis f-s calculations results

      self.cx = torch.randn(batch_size, hidden_size, device=self.device) # initialize cell state (for LSTM only)

    def forward(self, event_times, event_type):
      """Input parameters:
          event_times - interarrival times between events

      """
        
      hidden_states, intensity_values = [], []
      batch_size, batch_len = event_times.shape

      # init hidden states
      self.init_hidden(batch_size, self.hidden_size)

      # for each time step (here X shape is (batch_size, seq_len, n_features) )
      for i in range(batch_len):

          #self.hx = self.rnn(event_times[:,i].reshape(-1,1), self.hx) # uncomment if you use RNN
          self.hx, self.cx = self.rnn(event_times[:,i].reshape(-1,1), (self.hx, self.cx)) # uncomment if you use LSTM
          self.parameters = self.h2p(self.hx)
          
          intensity = self.intensity_layer(event_times[:,i])
          hidden_states.append(self.hx)
          intensity_values.append(intensity)

      # make predictions
      #print("'intensity_values' length ", len(intensity_values))
      #print("'torch.stack(intensity_values)' shape is ", torch.stack(intensity_values).shape)
      #stack_intensity.append(torch.stack(intensity_values))
      time_pred  = self.time_predict(batch_size, hidden_states)
                    
      return  torch.stack(intensity_values), time_pred

    def LogLikelihoodLoss(self, intensity, event_times):
        """
        Inputs:
            intensity (S, B) - intensity values,
            event_times (B, S) - inter-arrival times of events
        """

        # Compute log-likelihood of of the events that happened (first term) via sum of log-intensities 
        original_loglikelihood = intensity.log().sum(dim=0)

        #Compute log-probabilities of non-events (second term) using Monte Carlo method

        #Calc intensity of simulated events
        sim_times = create_unifrom_d(event_times, self.device)
        sim_intesity = []
        for i in range(sim_times.shape[1]):
            sim_intesity.append(self.intensity_layer(sim_times[:,i]))

        sim_intesity = torch.stack(sim_intesity).to(self.device)
        tot_time_seqs, seq_len = event_times.sum(dim=1), event_times.shape[1]
        mc_coef = (tot_time_seqs / seq_len)

        simulated_likelihood = sim_intesity.sum(dim=0) * mc_coef
        
        # sum over batch
        LLH = (original_loglikelihood - simulated_likelihood).sum()

        return -LLH

    def time_predict(self, batch_size, hidden_states):
        # output prediction layer
        #print(" In time predict function length of hidden_states is ", torch.stack(hidden_states).shape)
        time_prediction = self.time_predictor(torch.stack(hidden_states))
        
        return time_prediction


    def time_error(self, time_pred, time):
        """
        Function to compute mean squared error for time predictions.
        Input:
            time_pred (B, S) - time predictions,
            time (B, S) - ground truth for times
        Output:
            time_error (float) - time prediction error for the whole batch
        """

        time_ground_truth = time[:, 1:] # - time[:, :-1]
        time_pred = time_pred[:-1, :]

        time_error = nn.MSELoss(reduction='mean')(time_pred, time_ground_truth)
        return time_error
