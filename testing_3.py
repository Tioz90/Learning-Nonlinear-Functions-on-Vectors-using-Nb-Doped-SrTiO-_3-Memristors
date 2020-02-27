from neuromorphic_library_3 import MemristorArray
import neuromorphic_library_3 as nm
import nengo
import numpy as np

# import nengo_ocl

# hyperparameters
input_period = 4.0
input_frequency = 1 / input_period
pre_nrn = 4
post_nrn = 4
type = "pair"
spike_learning = True
function_to_learn = lambda x: x
simulation_time = 30
simulation_step = 0.001
error_delay = 5

with nengo.Network() as model:
    inp = nengo.Node(
            output=lambda t: np.sin( input_frequency * 2 * np.pi * t ),
            # output=nengo.processes.Piecewise( {
            #         5 : 0.2,
            #         10: 0.4,
            #         15: 0.6,
            #         20: 0.8,
            #         25: 1.0
            # } ),
            size_out=1,
            label="Input"
    )
    
    
    def generate_encoders( n_neurons ):
        if n_neurons % 2 == 0:
            return [ [ -1 ] ] * int( (n_neurons / 2) ) + [ [ 1 ] ] * int( (n_neurons / 2) )
        else:
            return [ [ -1 ] ] * int( (n_neurons / 2) ) + [ [ 1 ] ] + [ [ 1 ] ] * int( (n_neurons / 2) )
    
    
    # TODO use Izichevich model instead of LIF?
    pre = nengo.Ensemble( pre_nrn,
                          dimensions=1,
                          # encoders=generate_encoders( pre_nrn ),
                          label="Pre",
                          seed=2 )
    post = nengo.Ensemble( post_nrn,
                           dimensions=1,
                           # encoders=generate_encoders( post_nrn ),
                           label="Post",
                           seed=2 )
    
    memr_arr = MemristorArray( function=function_to_learn,
                               in_size=pre_nrn,
                               out_size=post_nrn,
                               dimensions=[ pre.dimensions, post.dimensions ],
                               type=type,
                               spike_learning=spike_learning,
                               error_delay=1 )
    learn = nengo.Node( memr_arr,
                        size_in=pre_nrn + pre.dimensions + post.dimensions,
                        size_out=post_nrn,
                        label="Learn" )
    
    nengo.Connection( inp, pre )
    nengo.Connection( pre.neurons, learn[ :pre_nrn ], synapse=0.01 )
    # decoded activities for error calculation
    nengo.Connection( pre, learn[ pre_nrn:pre_nrn + pre.dimensions ], synapse=0.01 )
    nengo.Connection( post, learn[ pre_nrn + pre.dimensions: ], synapse=0.01 )
    ##
    nengo.Connection( learn, post.neurons, synapse=None )
    
    inp_probe = nengo.Probe( inp )
    pre_spikes_probe = nengo.Probe( pre.neurons )
    post_spikes_probe = nengo.Probe( post.neurons )
    pre_probe = nengo.Probe( pre, synapse=0.01 )
    post_probe = nengo.Probe( post, synapse=0.01 )
    
    
    # nm.plot_network( model )
    
    def inhibit( t ):
        return 2.0 if t > 20.0 else 0.0
    
    # inhib = nengo.Node( inhibit )
    # nengo.Connection( inhib, err.neurons, transform=[ [ -1 ] ] * err.n_neurons )

with nengo.Simulator( model, dt=simulation_step ) as sim:
    sim.run( simulation_time )

nm.plot_ensemble_spikes( sim, "Pre", pre_spikes_probe, pre_probe )
nm.plot_ensemble_spikes( sim, "Post", post_spikes_probe, post_probe )
nm.plot_pre_post( sim, pre_probe, post_probe, inp_probe, memr_arr.get_error() )
memr_arr.plot_state( sim, "conductance", combined=True )