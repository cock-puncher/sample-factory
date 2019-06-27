import time
from multiprocessing import Process
from unittest import TestCase

import cv2

from envs.doom import concat_grid
from envs.doom import doom_env_by_name, make_doom_multiagent_env
from utils.utils import log, AttrDict


class TestDoom(TestCase):
    @staticmethod
    def doom_multiagent(worker_index, num_steps=1000):
        env_config = AttrDict({'worker_index': worker_index, 'vector_index': 0})
        multi_env = make_doom_multiagent_env(
            doom_env_by_name('doom_dm'), env_config=env_config,
        )

        obs = multi_env.reset()

        visualize = False
        start = time.time()

        for i in range(num_steps):
            actions = {key: multi_env.action_space.sample() for key in obs.keys()}
            obs, rew, dones, infos = multi_env.step(actions)

            if visualize:
                obs_display = [o['obs'] for o in obs.values()]
                obs_grid = concat_grid(obs_display)
                cv2.imshow('vizdoom', obs_grid)
                cv2.waitKey(1)

            if i % 100 == 0 or any(dones.values()):
                log.info('Rew %r done %r info %r', rew, dones, infos)

            # for player, info in infos.items():
            #     if 'HEALTH' in info:
            #         if info['HEALTH'] < -10:
            #             log.info('Player %r health: %.3f (%.3f)', player, info['HEALTH'], obs[player]['measurements'][2])

            for player, o in obs.items():
                health = o['measurements'][2]
                if health < -3:
                    log.info('Player %r health: %.3f', player, health)

            if dones['__all__']:
                multi_env.reset()

        took = time.time() - start
        log.info('Took %.3f seconds for %d steps', took, num_steps)
        log.info('Server steps per second: %.1f', num_steps / took)
        log.info('Observations fps: %.1f', num_steps * multi_env.num_players / took)
        log.info('Environment fps: %.1f', num_steps * multi_env.num_players * multi_env.skip_frames / took)

        multi_env.close()

    def test_doom_multiagent(self):
        self.doom_multiagent(worker_index=0)

    def test_doom_multiagent_parallel(self):
        num_workers = 16
        workers = []

        for i in range(num_workers):
            log.info('Starting worker #%d', i)
            worker = Process(target=self.doom_multiagent, args=(i, 200))
            worker.start()
            workers.append(worker)

        for i in range(num_workers):
            workers[i].join()