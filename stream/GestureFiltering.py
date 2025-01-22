import numpy as np
from hmmlearn import hmm




class GestureFilteringHMM:
    def __init__(self, num_states, start_neg_prob=0.5, trans_self_prob=0.9, emit_self_prob=0.9):
        """
        Initialize the HMM model.
        
        :param num_states: Number of hidden states (e.g., gestures)
        :param start_prob: Initial state probabilities (array of size num_states)
        :param trans_prob: Transition probability matrix (size num_states x num_states)
        :param emit_prob: Emission probability matrix (size num_states x num_classes)
        """
        self.num_states = num_states
        self.start_prob = self._initialize_start_probabilities(negative_prob=start_neg_prob)
        assert np.isclose(self.start_prob.sum(), 1, atol=1e-6), f"Start probabilities must sum to 1, {self.start_prob}, {self.start_prob.sum()}"
        #print(self.start_prob)
        self.trans_prob = self._initialize_transition_matrix(same_prob=trans_self_prob)
        assert self.trans_prob.sum(axis=1).all() == 1, "Transition probabilities must sum to 1"
        #print(self.trans_prob)
        self.emit_prob = self._initialize_emission_probs(same_prob=emit_self_prob)
        assert self.emit_prob.sum(axis=1).all() == 1, "Emission probabilities must sum to 1"
        #print(self.emit_prob)
        self.current_belief = self.start_prob.copy()  # Initialize belief state
        self.most_likely_sequence = []  # Sequence of most likely states
        
    def _initialize_transition_matrix(self, same_prob = 0.9):
        """
        Initializes the transition matrix where negative class has a higher probability to persist.
        
        :return: A transition matrix of size num_classes x num_classes
        """
        # Start with a default matrix, where negative class (index 0) is likely to persist
        matrix = np.full((self.num_states, self.num_states), (1-same_prob)/(self.num_states-1))
        np.fill_diagonal(matrix, same_prob)  # Set higher probability for staying in the same class

        # Ensure that the sum of each row equals 1
        matrix = matrix / matrix.sum(axis=1, keepdims=True)

        return matrix

    def _initialize_emission_probs(self, same_prob = 0.9):
        """
        Initializes the emission probabilities, with higher probability for negative class.
        
        :return: A matrix of size num_states x num_classes
        """
        matrix = np.full((self.num_states, self.num_states), (1-same_prob)/(self.num_states-1))
        np.fill_diagonal(matrix, same_prob)  # Set higher probability for negative class being predicted

        # Normalize each row to sum to 1
        matrix = matrix / matrix.sum(axis=1, keepdims=True)

        return matrix

    def _initialize_start_probabilities(self, negative_prob = 0.5):
        """
        Initializes the start probabilities with a higher probability for the negative class.
        
        :return: A vector of size num_classes
        """
        start_prob = np.full(self.num_states, (1-negative_prob)/(self.num_states-1))
        start_prob[0] = negative_prob  # Higher probability for starting in the negative class
        start_prob = start_prob / start_prob.sum()  # Normalize to sum to 1
        return start_prob

    def update(self, observation_probs):
        """
        Update the belief state with new observation probabilities.
        
        :param observation_probs: Array of observation probabilities (size num_classes)
        :return: Updated belief state (array of size num_states)
        """
        observation_probs = np.array(observation_probs)
        
        observation_probs = observation_probs.squeeze()
        assert observation_probs.ndim == 1, "Observation probabilities must be a 1D array"
        
        if observation_probs.sum() != 1:
            observation_probs = observation_probs / observation_probs.sum()
        #print("Raw", observation_probs)
        
        # Compute updated belief state (Bayesian filtering)
        updated_belief = self.emit_prob @ observation_probs
        updated_belief = (self.trans_prob @ self.current_belief) * updated_belief

        # Normalize the updated belief state to a distribution
        self.current_belief = updated_belief / updated_belief.sum()

        # Update the most likely state
        most_likely_state_idx = np.argmax(self.current_belief)
        self.most_likely_sequence.append(most_likely_state_idx)

        #print("Updated", self.current_belief)
        return self.current_belief

    def get_most_likely_sequence(self):
        """
        Get the most likely sequence of states.
        
        :return: List of most likely states
        """
        return self.most_likely_sequence

def test_gesture_filtering_hmm():
    """
    Test function for GestureFilteringHMM.
    """
    # Define test parameters
    num_states = 9


    # Observations (probabilities) for test
    true_gesture = np.array([0]*10 + [1]*5 + [0]*10)
    predicted_probailities = np.zeros((len(true_gesture), num_states))
    predicted_probailities[np.arange(len(true_gesture)), true_gesture] = 1
    
    #add some noise
    predicted_probailities += np.random.normal(0, 0.1, predicted_probailities.shape)
    
    #smooth it
    predicted_probailities = np.apply_along_axis(lambda x: np.convolve(x, np.ones(3)/1, mode='same'), axis=0, arr=predicted_probailities)
    
    #softmax
    observations = np.exp(predicted_probailities) / np.exp(predicted_probailities).sum(axis=1, keepdims=True)
    print(observations)
    # Initialize HMM
    hmm = GestureFilteringHMM(num_states)
    
    hmm.trans_prob[8, :] = 0
    # you can only transition to 6 from 5 and 8
    hmm.trans_prob[6, :] = 0
    # from state 5 you can either go to 5 or 8
    hmm.trans_prob[:, 5] = [0, 0, 0, 0, 0, 0.9, 0, 0, 0.1]
    # from state 8 you can eithet go to 8 or 6
    hmm.trans_prob[:, 8] = [0, 0, 0, 0, 0, 0, 0.1, 0, 0.9]

    
    # normalize
    hmm.trans_prob = hmm.trans_prob / hmm.trans_prob.sum(axis=0, keepdims=True)
    
    
    # 8 is never emitted, but it's possible to observe 0 when in state 8
    hmm.emit_prob[0,8] += hmm.emit_prob[8,8]
    hmm.emit_prob[8,8] = 0

    # Run through observations and test updates
    for t, obs in enumerate(observations):
        belief_state = hmm.update(obs)
        print(f"Timestep {t + 1}: Belief state = {belief_state}, Predicted state = {np.argmax(belief_state)}")



if __name__ == "__main__":
    test_gesture_filtering_hmm()