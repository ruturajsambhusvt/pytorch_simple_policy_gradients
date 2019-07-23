from policy import Softmax_Policy
from policy import ValueNetwork
import torch
from torch.autograd import Variable
import torch.autograd as autograd
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

class REINFORCE_discrete:
    '''
    Implementation of basic reinforce for discrete action spaces
    '''

    def __init__(self, num_inputs, hidden_size, action_space, lr_pi = 3e-4,\
                 lr_vf = 1e-3, baseline = False, gamma = 0.99, train_v_iters = 1):

        self.gamma = gamma
        self.action_space = action_space
        self.policy = Softmax_Policy(num_inputs, hidden_size, action_space)# use a different policy depending on the action space being continuous or note.
        self.policy_optimizer = optim.Adam(self.policy.parameters(), lr = lr_pi)
        self.baseline = baseline
        self.train_v_iters = train_v_iters # how many times you want to run update loop.

        # create value network if we want to use baseline/advantage
        if self.baseline:

            self.value_function = ValueNetwork(num_inputs, hidden_size)
            self.value_optimizer = optim.Adam(self.value_function.parameters(), lr = lr_vf)

    def select_action(self,state):

    	state = torch.from_numpy(state).float().unsqueeze(0)
    	probs = self.policy(state)
    	m = Categorical(probs)
    	action = m.sample()
	log_prob = m.log_prob(action)

	return action.item(), log_prob

    def train(self, trajectory):

        '''
        The training is done using the rewards-to-go formulation of the policy gradient update of Reinforce.
        If we are using a baseline, the value network is also trained.
        trajectory: a list of the form [( state , action , lnP(a_t|s_t), reward ), ...  ]
        '''

        log_probs = [item[2] for item in trajectory]
        rewards = [item[3] for item in trajectory]
        states = [item[0] for item in trajectory]
        actions = [item[1] for item in trajectory]

	#calculate rewards to go
        R = 0
        returns = []
        for r in rewards[::-1]:
            R = r + self.gamma * R
            returns.insert(0, R)

        returns = torch.tensor(returns)

        # train the Value Network and calculate Advantage
        if self.baseline:

            # loop over this a couple of times
            for _ in range(self.train_v_iters):
                # calculate loss of value function using mean squared error
                value_estimates = []
                for state in states:
                    state = torch.from_numpy(state).float().unsqueeze(0) # just to make it a Tensor obj
                    value_estimates.append( self.value_function(state) )

                value_estimates = torch.stack(value_estimates).squeeze() # rewards to go for each step of env trajectory

                v_loss = F.mse_loss(value_estimates, returns)
                # update the weights
                self.value_optimizer.zero_grad()
                v_loss.backward()
                self.value_optimizer.step()

            # calculate advantage
            advantage = []
            for value, R in zip(value_estimates, returns):
                advantage.append(R - value)

            advantage = torch.Tensor(advantage)

            # caluclate policy loss
            policy_loss = []
            for log_prob, adv in zip(log_probs, advantage):
                policy_loss.append( - log_prob * adv)


        else:
            policy_loss = []
            for log_prob, R in zip(log_probs, returns):
                policy_loss.append( - log_prob * R)


        policy_loss = torch.stack( policy_loss ).sum()
        # update policy weights
        self.policy_optimizer.zero_grad()
        policy_loss.backward()
        self.policy_optimizer.step()


        if self.baseline:
            return policy_loss, v_loss

        else:
            return policy_loss


