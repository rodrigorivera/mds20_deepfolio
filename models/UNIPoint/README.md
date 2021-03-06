<h2 align="center"> UNIPoint </h2>

<h4 align="center"> Content </h4>

<p align="center">
  <a href="#architecture">Architecture</a> •
  <a href="#implementation-details">Implementation details</a> •
  <a href="#loss-function">Loss function</a>
</p>

## Architecture

The main idea behind this neural network is that for a given dataset of event sequences <img src="https://latex.codecogs.com/png.latex?\{t_i\}_{i=1}^N" /></a> and corresponding intterarrival times <img src="https://latex.codecogs.com/png.latex?\tau_i&space;=&space;t_i&space;-&space;t_{i-1}" /></a> UNIPoint produces an intensity function <img src="https://latex.codecogs.com/png.latex?\hat{\lambda}" /></a>. In order to do this, UNIPoint combines a RNN with a transfer function and a sum of basis functions. 

The architecture could be seen on the image below (taken from <a href="https://paperpile.com/shared/uEtljl" target="_blank">Universal Approximation with Neural Intensity Point Processes</a>):

<p align="center">
  <img width="680" height="275" src="https://github.com/rodrigorivera/mds20_deepfolio/blob/main/images/unipoint_fig.PNG">
</p>

On the left side of the picture it is shown how UNIPoint generates the point process intensity for the entire sequence. For each interarrival time, the RNN (blue circle) feeds into a multi-layer perceptron (green square) to produce a point process intensity.

From the right side a more detailed view is given. It is showing how UNIPoint adds multiple basis functions to create the intensity function. <img src="https://latex.codecogs.com/png.latex?p_0"/></a>, <img src="https://latex.codecogs.com/png.latex?p_1"/></a>, <img src="https://latex.codecogs.com/png.latex?p_2"/></a>, <img src="https://latex.codecogs.com/png.latex?p_3"/></a> are the basis functions parameters generated by the neural network using the hidden state <img src="https://latex.codecogs.com/png.latex?h_1"/></a> and interarrival time <img src="https://latex.codecogs.com/png.latex?\tau_2" /></a>

## Implementation details

Since the implementation from authors **is not available**, we are going to implement the model according to the paper description. For this we are going to use PyTorch layers from *torch.nn*.

* **Vanilla RNN** is going to be used to produce hidden states <img src="https://latex.codecogs.com/png.latex?h_i&space;\in&space;R^M" /></a> (although the paper states that LSTM or GRU can also be used). Vanilla RNN is defined as:
<img src="https://latex.codecogs.com/png.latex?h_i&space;=&space;f(Wh_{i-1}&space;&plus;&space;v\tau_i&space;&plus;&space;b)" /></a>
where <img src="https://latex.codecogs.com/png.latex?W,&space;v,&space;b,&space;h_0" /></a> are learnable parameters and <img src="https://latex.codecogs.com/png.latex?f" /></a> is an activation function (for example, like the sigmoid in <a href="https://link.springer.com/chapter/10.1007/11840817_66" target="_blank">Schäfer and Zimmermann (2007)</a>).

* To generate **parameters for our basis functions**, we define a linear transformation from the RNN hidden state vector into parameter matrix:
<img src="https://latex.codecogs.com/png.latex?P&space;=&space;Ah_i&space;&plus;&space;B,&space;t_i&space;<&space;t&space;\leq&space;t_{i&plus;1}" /></a>
where <img src="https://latex.codecogs.com/png.latex?P&space;\in&space;R^{J\times&space;|\mathcal{P}|},&space;A&space;\in&space;R^{J\times&space;|\mathcal{P}|},&space;B&space;\in&space;R^{J\times&space;|\mathcal{P}|}" /></a>. Further we can define <img src="https://latex.codecogs.com/png.latex?p_j&space;\doteq&space;P_{(j,\cdot&space;)}&space;\in&space;R^{|\mathcal{P}|}" /></a> for <img src="https://latex.codecogs.com/png.latex?j&space;\in&space;\{&space;1,...,J\}" /></a>, which corresponds to the parameter of the j-th basis function at some time <img src="https://latex.codecogs.com/png.latex?t_i&space;<&space;t&space;\leq&space;t_{i&plus;1}" /></a>

* **The intensity function** with parameters <img src="https://latex.codecogs.com/png.latex?p_1,...,p_J" /></a> with respect to interarrival time <img src="https://latex.codecogs.com/png.latex?\tau&space;=&space;t&space;-&space;t_i" /></a> could be defined as:
<img src="https://latex.codecogs.com/png.latex?\hat{\lambda}(\tau)&space;=&space;f_{SP}&space;[\sum_{j=1}^J&space;\phi(\tau;p_j)],&space;t_i&space;<&space;t&space;\leq&space;t_{i&plus;1}" /></a>
where <img src="https://latex.codecogs.com/png.latex?f_{SP}(x)&space;=&space;log(1&plus;e^x)" /></a> is the softplus function.
The interarrival times can be also normalised by their standard deviation in order to avoid numerical issues.

* For the **basis functions** we are planning to test all functions suggested by the authors in the table below, they are: power law function, exponential function, cosinus, sigmoid, ReLU and some combinations of them (PL + ReLU). We also will test different numbers of basis function in the model {2, 4, 8, 16, 32}.

<p align="center">
  <img width="400" height="200" src="https://github.com/rodrigorivera/mds20_deepfolio/blob/main/images/basis_func.PNG">
</p>

## Loss function

* For **loss function** the point process negative log-likelihood is going to be used.
<img src="https://latex.codecogs.com/png.latex?L&space;=&space;[\prod_{i=1}^N&space;\lambda^*(t_i)]&space;exp(\int_{0}^{T}&space;\lambda^*(s)ds))"  /></a>

* For **loss calculation** authors suggest to use Monte-Carlo integration with 200 per event interval, but it can be done differently - through linear interpolation or trapezoidal rule.
