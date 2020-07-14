import tensorflow as tf
import numpy as np
import copy

# tf.compat.v1.disable_eager_execution()

output_size = input_size = 4

local_error_np = np.array( [ -8.60119821, 10.69191986, 19.24545064, -2.81894391 ], dtype=np.float32 )
# local_error_np = np.array( [ 1e-6, 1e-6, 1e-6, 1e-6 ], dtype=np.float32 )
pre_filtered_np = np.array( [ 0., 0., 0., 148.41070704 ], dtype=np.float32 )
pos_memristors_np = np.array( [ [ 1.05928446e+08, 1.08442657e+08, 1.08579456e+08, 1.08472517e+08 ],
                                [ 1.06235637e+08, 1.03843817e+08, 1.02975346e+08, 1.00567130e+08 ],
                                [ 1.02726563e+08, 1.04776651e+08, 1.08121687e+08, 1.04799772e+08 ],
                                [ 1.03927848e+08, 1.08360788e+08, 1.03373962e+08, 1.06481719e+08 ] ], dtype=np.float32 )
neg_memristors_np = np.array( [ [ 1.03682415e+08, 1.09571552e+08, 1.01403508e+08, 1.08700873e+08 ],
                                [ 1.04736080e+08, 1.08009108e+08, 1.05204775e+08, 1.06788795e+08 ],
                                [ 1.07206327e+08, 1.05820198e+08, 1.05373732e+08, 1.07586156e+08 ],
                                [ 1.01059076e+08, 1.04736004e+08, 1.01863323e+08, 1.07369182e+08 ] ], dtype=np.float32 )

local_error_tf = tf.reshape(
        tf.convert_to_tensor( local_error_np ),
        [ 1, 1, input_size, 1 ]
        )
pre_filtered_tf = tf.reshape(
        tf.convert_to_tensor( pre_filtered_np ),
        [ 1, 1, 1, input_size ]
        )
pos_memristors_tf = tf.reshape(
        tf.convert_to_tensor( pos_memristors_np ),
        [ 1, 1, output_size, input_size ]
        )
neg_memristors_tf = tf.reshape(
        tf.convert_to_tensor( neg_memristors_np ),
        [ 1, 1, output_size, input_size ]
        )


def np_calc( local_error, pre_filtered, pos_memristors, neg_memristors ):
    a = -0.1
    r_min = 1e2
    r_max = 2.5e8
    g_min = 1.0 / r_max
    g_max = 1.0 / r_min
    error_threshold = 1e-5
    gain = 1e5
    
    def resistance2conductance( R ):
        g_curr = 1.0 / R
        g_norm = (g_curr - g_min) / (g_max - g_min)
        
        return g_norm * gain
    
    def find_spikes( input_activities, shape, output_activities=None, invert=False ):
        output_size = shape[ 0 ]
        input_size = shape[ 1 ]
        spiked_pre = np.tile(
                np.array( np.rint( input_activities ), dtype=bool ), (output_size, 1)
                )
        spiked_post = np.tile(
                np.expand_dims(
                        np.array( np.rint( output_activities ), dtype=bool ), axis=1 ), (1, input_size)
                ) \
            if output_activities is not None \
            else np.ones( (1, input_size) )
        
        out = np.logical_and( spiked_pre, spiked_post )
        return out if not invert else np.logical_not( out )
    
    if np.any( np.absolute( local_error ) > error_threshold ):
        pes_delta = np.outer( -local_error, pre_filtered )
        
        spiked_map = find_spikes( pre_filtered, (output_size, input_size), invert=True )
        pes_delta[ spiked_map ] = 0
        
        V = np.sign( pes_delta ) * 1e-1
        
        n_pos = ((pos_memristors[ V > 0 ] - r_min) / r_max)**(1 / a)
        n_neg = ((neg_memristors[ V < 0 ] - r_min) / r_max)**(1 / a)
        
        pos_update = r_min + r_max * (n_pos + 1)**a
        neg_update = r_min + r_max * (n_neg + 1)**a
        pos_memristors[ V > 0 ] = pos_update
        neg_memristors[ V < 0 ] = neg_update
    
    return pos_memristors, neg_memristors
    #
    # return resistance2conductance( pos_memristors[ : ] ) \
    #        - resistance2conductance( neg_memristors[ : ] )


# @tf.function
def tf_calc( local_error, pre_filtered, pos_memristors, neg_memristors ):
    r_min = tf.constant( 1e2 )
    r_max = tf.constant( 2.5e8 )
    a = tf.constant( -0.1 )
    error_threshold = tf.constant( 1e-5 )
    
    def find_spikes( input_activities, output_size, invert=False ):
        spiked_pre = tf.cast(
                tf.tile( tf.math.rint( input_activities ), [ 1, 1, output_size, 1 ] ),
                tf.bool )
        
        out = spiked_pre
        if invert:
            out = tf.math.logical_not( out )
        
        return tf.cast( out, tf.float32 )
    
    def if_error_over_threshold( pos_memristors, neg_memristors ):
        # if tf.reduce_any( tf.greater( tf.abs( local_error ), error_threshold ) ):
        pes_delta = -local_error * pre_filtered
        
        spiked_map = find_spikes( pre_filtered, output_size )
        pes_delta = pes_delta * spiked_map
        
        V = tf.sign( pes_delta ) * 1e-1
        
        pos_mask = tf.greater( V, 0 )
        pos_indices = tf.where( pos_mask )
        pos_n = ((tf.boolean_mask( pos_memristors, pos_mask ) - r_min) / r_max)**(1 / a)
        pos_update = r_min + r_max * (pos_n + 1)**a
        pos_memristors = tf.tensor_scatter_nd_update( pos_memristors, pos_indices, pos_update )
        
        neg_mask = tf.less( V, 0 )
        neg_indices = tf.where( neg_mask )
        neg_n = ((tf.boolean_mask( neg_memristors, neg_mask ) - r_min) / r_max)**(1 / a)
        neg_update = r_min + r_max * (neg_n + 1)**a
        neg_memristors = tf.tensor_scatter_nd_update( neg_memristors, neg_indices, neg_update )
        
        return pos_memristors, neg_memristors
    
    cond_out = tf.cond( tf.reduce_any( tf.greater( tf.abs( local_error ), error_threshold ) ),
                        true_fn=lambda: if_error_over_threshold( pos_memristors, neg_memristors ),
                        false_fn=lambda: (tf.identity( pos_memristors ), tf.identity( neg_memristors )) )
    
    return cond_out


iterations = 1
for i in range( iterations ):
    print( "Iteration", i )
    
    pos_mem_np, neg_mem_np = np_calc( local_error_np,
                                      pre_filtered_np,
                                      copy.deepcopy( pos_memristors_np ),
                                      copy.deepcopy( neg_memristors_np ) )
    pos_mem_tf, neg_mem_tf = tf_calc( local_error_tf,
                                      pre_filtered_tf,
                                      pos_memristors_tf,
                                      neg_memristors_tf )
    
    print( "NumPy\n", pos_mem_np, "\n", neg_mem_np )
    print( "TensorFlow\n", pos_mem_tf.numpy(), "\n", neg_mem_tf.numpy() )
    print( "tf and np are equal?",
           np.array_equal( pos_mem_np, pos_mem_tf.numpy().squeeze() )
           and np.array_equal( neg_mem_np, neg_mem_tf.numpy().squeeze() )
           )
    print( "Before\n", pos_memristors_np, "\n", neg_memristors_np )
    print( "After\n", pos_mem_np, "\n", neg_mem_np )
    print( "before and after are equal?",
           np.array_equal( pos_mem_np, pos_memristors_np )
           and np.array_equal( neg_mem_np, neg_memristors_np )
           )