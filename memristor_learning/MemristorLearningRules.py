import numpy as np


class MemristorLearningRule:
    def __init__( self, learning_rate, dt=0.001 ):
        self.learning_rate = learning_rate
        self.dt = dt
        
        # only used in supervised rules (ex. mPES)
        self.last_error = None
        
        self.input_size = None
        self.output_size = None
        
        self.weights = None
        self.memristors = None
        self.logging = None
    
    def get_error_signal( self ):
        return self.last_error


class mOja( MemristorLearningRule ):
    def __init__( self, learning_rate=1e-6, dt=0.001, beta=1.0 ):
        super().__init__( learning_rate, dt )
        
        self.alpha = self.learning_rate * self.dt
        self.beta = beta
    
    def __call__( self, t, x ):
        input_activities = x[ :self.input_size ]
        output_activities = x[ self.input_size:self.input_size + self.output_size ]
        
        post_squared = self.alpha * output_activities * output_activities
        forgetting = -self.beta * self.weights * np.expand_dims( post_squared, axis=1 )
        hebbian = np.outer( self.alpha * output_activities, input_activities )
        update_direction = hebbian - forgetting
        
        # if self.logging:
        #     self.save_state()
        
        # squash spikes to False (0) or True (100/1000 ...) or everything is always adjusted
        spiked_pre = np.tile(
                np.array( np.rint( input_activities ), dtype=bool ), (self.output_size, 1)
                )
        spiked_post = np.tile(
                np.expand_dims( np.array( np.rint( output_activities ), dtype=bool ), axis=1 ), (1, self.input_size)
                )
        spiked_map = np.logical_and( spiked_pre, spiked_post )
        
        # we only need to update the weights for the neurons that spiked so we filter
        if spiked_map.any():
            for j, i in np.transpose( np.where( spiked_map ) ):
                self.weights[ j, i ] = self.memristors[ j, i ].pulse( update_direction[ j, i ],
                                                                      value="conductance",
                                                                      method="same"
                                                                      )
        
        # if self.logging:
        #     self.weight_history.append( self.weights.copy() )
        
        # calculate the output at this timestep
        return np.dot( self.weights, input_activities )


class mBCM( MemristorLearningRule ):
    def __init__( self, learning_rate=1e-9, dt=0.001 ):
        super().__init__( learning_rate, dt )
        
        self.alpha = self.learning_rate * self.dt
    
    def __call__( self, t, x ):
        
        input_activities = x[ :self.input_size ]
        output_activities = x[ self.input_size:self.input_size + self.output_size ]
        theta = x[ self.input_size + self.output_size: ]
        
        update_direction = output_activities - theta
        # function \phi( a, \theta ) that is the moving threshold
        update = self.alpha * output_activities * update_direction
        
        # if self.logging:
        #     self.save_state()
        
        # squash spikes to False (0) or True (100/1000 ...) or everything is always adjusted
        spiked_pre = np.tile(
                np.array( np.rint( input_activities ), dtype=bool ), (self.output_size, 1)
                )
        spiked_post = np.tile(
                np.expand_dims( np.array( np.rint( output_activities ), dtype=bool ), axis=1 ), (1, self.input_size)
                )
        spiked_map = np.logical_and( spiked_pre, spiked_post )
        
        # we only need to update the weights for the neurons that spiked so we filter
        if spiked_map.any():
            for j, i in np.transpose( np.where( spiked_map ) ):
                self.weights[ j, i ] = self.memristors[ j, i ].pulse( update_direction[ j ],
                                                                      value="conductance",
                                                                      method="same"
                                                                      )
        
        # if self.logging:
        #     self.weight_history.append( self.weights.copy() )
        
        # calculate the output at this timestep
        return np.dot( self.weights, input_activities )


class mPES( MemristorLearningRule ):
    def __init__( self, encoders, learning_rate=1e-5, dt=0.001 ):
        super().__init__( learning_rate, dt )
        
        self.encoders = encoders
    
    # TODO can I remove the inverse method from pulse?
    def __call__( self, t, x ):
        input_activities = x[ :self.input_size ]
        # squash error to zero under a certain threshold or learning rule keeps running indefinitely
        error = x[ self.input_size: ] if abs( x[ self.input_size: ] ) > 10**-5 else 0
        alpha = self.learning_rate * self.dt / self.input_size
        self.last_error = error
        
        # we are adjusting weights so calculate local error
        local_error = alpha * np.dot( self.encoders, error )
        
        # if self.logging:
        #     self.error_history.append( error )
        #     self.save_state()
        
        # squash spikes to False (0) or True (100/1000 ...) or everything is always adjusted
        spiked_map = np.tile(
                np.array( np.rint( input_activities ), dtype=bool ), (self.output_size, 1)
                )
        
        # we only need to update the weights for the neurons that spiked so we filter for their columns
        if spiked_map.any():
            for j, i in np.transpose( np.where( spiked_map ) ):
                self.weights[ j, i ] = self.memristors[ j, i ].pulse( local_error[ j ],
                                                                      value="conductance",
                                                                      method="inverse"
                                                                      )
        
        # if self.logging:
        #     self.weight_history.append( self.weights.copy() )
        
        # calculate the output at this timestep
        return np.dot( self.weights, input_activities )