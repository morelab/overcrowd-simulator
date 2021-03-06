import sparkunittest
import unittest
from device_gen import devices_generator, Device
from grid_manager import GridManager
import numpy
import random

class MockPositionGenerator():

    def __init__(self, nr_nodes, dimensions):
        self.nr_nodes = nr_nodes
        self.dimensions = dimensions

    def __iter__(self):
        while True:
            positions = []
            for i in range(self.nr_nodes):
                x = random.randint(0, self.dimensions[0])
                y = random.randint(0, self.dimensions[1])
                positions.append((x, y))

            yield positions

class TestDeviceGenerator(unittest.TestCase):

    def test_generation(self):
        model = MockPositionGenerator(nr_nodes=200, dimensions=(128, 128))

        devices_gen = devices_generator(model, accuracy=(20.0, 30.0))

        for i in range(10):
            devices = next(devices_gen)
            self.assertEqual(200, len(devices))

            device_ids = set([])
            for node_id, device in devices.items():
                device_ids.add(node_id)
                self.assertTrue(0 <= device.position[0] <= 200)
                self.assertTrue(0 <= device.position[1] <= 200)

                self.assertTrue(20.0 <= device.accuracy <= 30.0)

            self.assertEquals(200, len(devices.keys()))
            self.assertEquals(200, len(device_ids))

class TestGridManager(sparkunittest.SparkTestCase):

    def test_grid_manager(self):
        grid_manager = GridManager(spark_context=self.sc, dimensions=(250, 250), n_cells=(128, 128))

        self.assertEquals((250, 250), grid_manager.dimensions)
        self.assertEquals(62500, grid_manager.area)
        self.assertEquals((128, 128), grid_manager.n_cells)
        self.assertEquals((1.953125, 1.953125), grid_manager.cell_dimensions)
        self.assertEquals(3.814697265625, grid_manager.cell_area)

        self.assertEquals(128, grid_manager.rows)
        self.assertEquals(128, grid_manager.columns)

        for i in range(grid_manager.rows):
            for j in range(grid_manager.columns):
                expected_box = (
                    i * grid_manager.cell_dimensions[0],
                    j * grid_manager.cell_dimensions[1],
                    i * grid_manager.cell_dimensions[0] + grid_manager.cell_dimensions[0],
                    j * grid_manager.cell_dimensions[1] + grid_manager.cell_dimensions[1]
                )

                self.assertEquals(expected_box, grid_manager[i, j].box.bounds)

    def test_grid(self):
        dimensions_list = [(6, 6), (12, 12), (24, 24), (150, 150), (200, 200)]
        cell_sizes = [(2, 2), (4, 4), (8, 8), (32, 32)]
        for dimensions in dimensions_list:
            for n_cells in cell_sizes:
                grid_manager = GridManager(spark_context=self.sc, dimensions=dimensions, n_cells=n_cells)

                devices = [
                    Device("0", (1.0, 1.0), 1.0),
                    Device("1", (3.0, 3.0), 1.0),
                    Device("3", (2.0, 2.0), 1.0),
                    Device("2", (5.0, 5.0), 1.0),
                ]

                grid_manager.update(devices)

                self.assertEquals(n_cells, grid_manager.shape)
                self.assertEquals(n_cells[0], grid_manager.rows)
                self.assertEquals(n_cells[1], grid_manager.columns)
                cell_area = dimensions[0] / float(n_cells[0]) * dimensions[1] / float(n_cells[1])
                self.assertTrue(numpy.isclose(cell_area, grid_manager.cell_area))
                self.assertEquals(len(devices) / float(dimensions[0] * dimensions[1]), grid_manager.avg_density)

                self.assertTrue(numpy.isclose(len(devices), grid_manager.occupation_matrix.sum()))

                expected_avg_density = len(devices) / float(grid_manager.n_cells[0] * grid_manager.n_cells[1])
                self.assertTrue(expected_avg_density, grid_manager.density_matrix.mean())

    def test_wall_close_density(self):
        grid_manager = GridManager(spark_context=self.sc, dimensions=(4, 4), n_cells=(4, 4))

        devices = [
            Device("0", (0.0, 0.0), 1.0)
        ]

        grid_manager.update(devices)

        self.assertTrue(numpy.isclose(1.0, grid_manager.occupation_matrix.sum()))

    def test_outside_area(self):
        grid_manager = GridManager(spark_context=self.sc, dimensions=(4, 4), n_cells=(4, 4))

        devices = [
            Device("0", (-2.0, -2.0), 5.0)
        ]

        grid_manager.update(devices)

        print grid_manager.occupation_matrix

        self.assertTrue(numpy.isclose(1.0, grid_manager.occupation_matrix.sum()))

    def test_occupation_matrix(self):
        grid_manager = GridManager(spark_context=self.sc, dimensions=(8, 8), n_cells=(8, 8))

        devices = [
            Device("0", (1.0, 1.0), 1.0),
            Device("1", (3.0, 3.0), 1.0),
            Device("2", (2.0, 2.0), 1.0),
            Device("3", (5.0, 5.0), 1.0)
        ]

        grid_manager.update(devices)

        expected_matrix =  numpy.array(
            [[ 0.25,  0.25,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ],
             [ 0.25,  0.5 ,  0.25,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ],
             [ 0.  ,  0.25,  0.5 ,  0.25,  0.  ,  0.  ,  0.  ,  0.  ],
             [ 0.  ,  0.  ,  0.25,  0.25,  0.  ,  0.  ,  0.  ,  0.  ],
             [ 0.  ,  0.  ,  0.  ,  0.  ,  0.25,  0.25,  0.  ,  0.  ],
             [ 0.  ,  0.  ,  0.  ,  0.  ,  0.25,  0.25,  0.  ,  0.  ],
             [ 0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ],
             [ 0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ]]
        )

        self.assertTrue(numpy.allclose(expected_matrix, grid_manager.occupation_matrix))

    def test_check_density(self):
        grid_manager = GridManager(spark_context=self.sc, dimensions=(8, 8), n_cells=(8, 8))

        devices = [
            Device("0", (1.0, 1.0), 1.0),
            Device("1", (3.0, 3.0), 1.0),
            Device("2", (2.0, 2.0), 1.0),
            Device("3", (5.0, 5.0), 1.0)
        ]

        grid_manager.update(devices)

        expected_indices = [
            (1, 1), (2, 2)
        ]

        indices = grid_manager.check_density(lambda x: x > 0.3)
        self.assertTrue(numpy.array_equal(expected_indices, indices))

        indices = grid_manager.check_occupation(lambda x: x > 0.3)
        self.assertTrue(numpy.array_equal(expected_indices, indices))

    def test_check_occupation(self):
        grid_manager = GridManager(spark_context=self.sc, dimensions=(8, 8), n_cells=(4, 4))

        devices = [
            Device("0", (3.0, 3.0), 1.0),
        ]

        grid_manager.update(devices)

        expected_indices = [
            (1, 1)
        ]

        indices = grid_manager.check_occupation(lambda x: x >= 0.8)
        self.assertTrue(numpy.array_equal(expected_indices, indices))

if __name__ == '__main__':
    unittest.main()
