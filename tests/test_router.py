import unittest
import time
import uuid
import random
import asyncio
from blest import Router, BlestError

class TestRouter(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUp(cls):
        cls.router = Router({ 'timeout': 1000 })
        cls.benchmarks = []

        @cls.router.before_request()
        def middleware(body, context):
            context['test'] = {
                'value': body['testValue']
            }
            context['time'] = time.time()

        @cls.router.after_request()
        def trailing_middleware(_, context):
            complete_time = time.time()
            difference = complete_time - context['time']
            cls.benchmarks.append(difference)

        @cls.router.route('basicRoute')
        def basic_route(body, context):
            return {'route': 'basicRoute', 'body': body, 'context': context}

        router2 = Router({ 'timeout': 100 })

        @router2.route('mergedRoute')
        def merged_route(body, context):
            return {'route': 'mergedRoute', 'body': body, 'context': context}

        @router2.route('timeoutRoute')
        async def timeout_route(body, _):
            await asyncio.sleep(0.2)
            return {'testValue': body['testValue']}

        cls.router.merge(router2)

        router3 = Router()

        @router3.route('errorRoute')
        def error_route(body, _):
            error = BlestError(body['testValue'], code='ERROR_' + str(round(body['testValue'] * 10)))
            raise error

        cls.router.namespace('subRoutes', router3)

    async def run_routes(self):
        # Basic route
        self.testId1 = str(uuid.uuid4())
        self.testValue1 = random.random()
        self.result1, self.error1 = await self.router.handle([[self.testId1, 'basicRoute', {'testValue': self.testValue1}]], {'testValue': self.testValue1})

        # Merged route
        self.testId2 = str(uuid.uuid4())
        self.testValue2 = random.random()
        self.result2, self.error2 = await self.router.handle([[self.testId2, 'mergedRoute', {'testValue': self.testValue2}]], {'testValue': self.testValue2})

        # Error route
        self.testId3 = str(uuid.uuid4())
        self.testValue3 = random.random()
        self.result3, self.error3 = await self.router.handle([[self.testId3, 'subRoutes/errorRoute', {'testValue': self.testValue3}]], {'testValue': self.testValue3})

        # Missing route
        self.testId4 = str(uuid.uuid4())
        self.testValue4 = random.random()
        self.result4, self.error4 = await self.router.handle([[self.testId4, 'missingRoute', {'testValue': self.testValue4}]], {'testValue': self.testValue4})

        # Timeout route
        self.testId5 = str(uuid.uuid4())
        self.testValue5 = random.random()
        self.result5, self.error5 = await self.router.handle([[self.testId5, 'timeoutRoute', {'testValue': self.testValue5}]], {'testValue': self.testValue5})

        # Malformed request
        self.result6, self.error6 = await self.router.handle([[self.testId4], {}, [True, 1.25]])

    async def test_class_properties(self):
        self.assertIsInstance(self.router, Router)
        self.assertEqual(len(self.router.routes), 4)
        self.assertTrue(hasattr(self.router, 'handle'))

    async def test_valid_requests(self):
        await self.run_routes()
        self.assertIsNone(self.error1)
        self.assertIsNone(self.error2)
        self.assertIsNone(self.error3)
        self.assertIsNone(self.error4)
        self.assertIsNone(self.error5)

    async def test_matching_ids(self):
        await self.run_routes()
        self.assertEqual(self.result1[0][0], self.testId1)
        self.assertEqual(self.result2[0][0], self.testId2)
        self.assertEqual(self.result3[0][0], self.testId3)
        self.assertEqual(self.result4[0][0], self.testId4)
        self.assertEqual(self.result5[0][0], self.testId5)

    async def test_matching_routes(self):
        await self.run_routes()
        self.assertEqual(self.result1[0][1], 'basicRoute')
        self.assertEqual(self.result2[0][1], 'mergedRoute')
        self.assertEqual(self.result3[0][1], 'subRoutes/errorRoute')
        self.assertEqual(self.result4[0][1], 'missingRoute')
        self.assertEqual(self.result5[0][1], 'timeoutRoute')

    async def test_accept_parameters(self):
        await self.run_routes()
        self.assertAlmostEqual(float(self.result1[0][2]['body']['testValue']), self.testValue1)
        self.assertAlmostEqual(float(self.result2[0][2]['body']['testValue']), self.testValue2)

    async def test_respect_context(self):
        await self.run_routes()
        self.assertAlmostEqual(float(self.result1[0][2]['context']['testValue']), self.testValue1)
        self.assertAlmostEqual(float(self.result2[0][2]['context']['testValue']), self.testValue2)

    async def test_support_middleware(self):
        await self.run_routes()
        self.assertAlmostEqual(float(self.result1[0][2]['context']['test']['value']), self.testValue1)
        self.assertAlmostEqual(float(self.result2[0][2]['context']['test']['value']), self.testValue2)

    async def test_handle_errors(self):
        await self.run_routes()
        self.assertIsNone(self.result1[0][3])
        self.assertIsNone(self.result2[0][3])
        self.assertAlmostEqual(float(self.result3[0][3].get('message')), self.testValue3)
        self.assertEqual(self.result3[0][3].get('status'), 500)
        self.assertEqual(self.result3[0][3].get('code'), 'ERROR_' + str(round(self.testValue3 * 10)))
        self.assertEqual(self.result4[0][3].get('message'), 'Not Found')
        self.assertEqual(self.result4[0][3].get('status'), 404)

    async def test_timeout_setting(self):
        await self.run_routes()
        self.assertIsNone(self.result5[0][2])
        self.assertEqual(self.result5[0][3].get('message'), 'Internal Server Error')
        self.assertEqual(self.result5[0][3].get('status'), 500)

    async def test_reject_malformed_requests(self):
        await self.run_routes()
        self.assertIsNotNone(self.error6)

    async def test_trailing_middleware(self):
        await self.run_routes()
        self.assertEqual(len(self.benchmarks), 2)

    async def test_invalid_routes(self):
        with self.assertRaises(ValueError):
            @self.router.route('a')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('0abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('_abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('-abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc_')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc-')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/0abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/_abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/-abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('/abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc//abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/a/abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/0abc/abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/_abc/abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/-abc/abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/abc_/abc')
            def handler():
                pass

        with self.assertRaises(ValueError):
            @self.router.route('abc/abc-/abc')
            def handler():
                pass

if __name__ == '__main__':
    unittest.main()
