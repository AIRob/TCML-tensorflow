import tensorflow as tf
import numpy as np


class OmniglotEmbedNetwork:
    def __init__(self, input_queue, label_queue, batch_size):
        '''
         4 blocks of
           {3 × 3 conv (64 filters),
           batch normalization,
           leaky ReLU activation (leak 0.1),
           and 2 × 2 max-pooling}
        '''

        self.epsilon = 1e-3

        # input : B x T x H x W x C
        # output : B x T x D
        self.input_placeholder = input_queue.dequeue_many(batch_size)
        self.label_placeholder = label_queue.dequeue_many(batch_size)

        with tf.variable_scope("omni_embed_0"):
            last_output = self.add_block(self.input_placeholder, 1, 64)

        for i in [1, 2, 3]:
            with tf.variable_scope(f"omni_embed_{i}"):
                last_output = self.add_block(last_output, 64, 64)

        self.output = tf.squeeze(last_output)

    def add_block(self, x, in_channel, out_channel):
        kernel_size = [1, 3, 3, in_channel, out_channel]
        kernel = tf.get_variable("kernel", kernel_size, dtype=tf.float32,
                                 initializer=tf.contrib.layers.xavier_initializer_conv2d())
        conv_output = tf.nn.conv3d(x, kernel, [1, 1, 1, 1, 1], "SAME")

        batch_mean, batch_var = tf.nn.moments(conv_output, [0])
        batch_normalized = tf.nn.batch_normalization(conv_output, batch_mean, batch_var, None, None, self.epsilon)

        relu_output = tf.maximum(-0.1 * batch_normalized, batch_normalized, name="leaky_relu")

        return tf.nn.max_pool3d(relu_output, [1, 1, 2, 2, 1], [1, 1, 2, 2, 1], "VALID")


def _OmniglotEmbed_test():
    with tf.Graph().as_default():
        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        sess = tf.Session(config=config)

        dummy_input = np.random.rand(10, 28, 28, 1)
        queue = tf.RandomShuffleQueue(20,
                                      min_after_dequeue=2,
                                      shapes=dummy_input.shape, dtypes=tf.float32)
        enqueue = queue.enqueue(dummy_input)
        qr = tf.train.QueueRunner(queue, [enqueue] * 2)
        tf.train.add_queue_runner(qr)

        coord = tf.train.Coordinator()
        enqueue_threads = qr.create_threads(sess, coord=coord, start=True)

        model = OmniglotEmbedNetwork(queue, queue, 5) # second queue is dummy

        with sess.as_default():
            init = tf.initialize_all_variables()
            sess.run(init)

            output, = sess.run([model.output])
            print(output.shape)

            coord.request_stop()
            coord.join(enqueue_threads)

if __name__ == "__main__":
    _OmniglotEmbed_test()
