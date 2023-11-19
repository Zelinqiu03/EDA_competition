'''
Author       : luoweiWHUT 1615108374@qq.com
Date         : 2023-11-07 14:48:53
LastEditors  : luoweiWHUT 1615108374@qq.com
LastEditTime : 2023-11-19 18:06:02
FilePath     : \EDA_competition\main.py
Description  : 
'''
# import torch
import json
import sys
import copy
import time
import numpy as np
import random as rd
from solver import *
from solver_cplus import run_SA
from data_parse import Parser


def init_SA(state, reward, best_state, best_reward):
    ''' 
    description : 计算适合的模拟退火初始参数及部分通用参数
    return       init_state, init_reward, T, T_min,a(降温速度)
    '''
    # state = encode(mos_list, encode_dict)
    # reward = get_score(state, pins)
    N = 5*len(mos_list)
    count, sum_cost = 0, 0
    while count < N:
        action = rd.randint(0, Action_num-1)
        new_state = v_compute(state, action)
        new_reward = get_score(new_state, pins_code, ref_width)
        if new_reward < reward:
            count += 1
            sum_cost += reward-new_reward
        else:
            if best_reward < new_reward:
                best_state = new_state
                best_reward = new_reward
            state = new_state
            reward = new_reward
    return state, reward, best_state, best_reward, 2*sum_cost/N, 2*sum_cost/N/100


if __name__ == "__main__":
    start = time.time()
    if len(sys.argv) < 4:
        print(
            "ERROR: No enough file provided.\nUsage: python main.py  <netlist> <cell_name> <save_path>")
        exit()
    cell_spi_path, cell_name, save_path = sys.argv[1], sys.argv[2], sys.argv[3]
    paser = Parser()
    mos_list, pins = paser.parse(cell_spi_path, cell_name)
    encode_dict, decode_dict = paser.build_code_dict(cell_name)
    pins_code = [encode_dict['net'][net] for net in pins]
    ref_width = paser.cell_ref_width_dict[cell_name]
    # print(f"cell:{cell_name}\n晶体管数量:{len(mos_list)}")
    # print(f"使用{[i.name for i in use_algorithms]}算法优化...")
    """初始化"""
    if Algorithm.RL in use_algorithms:
        import torch
        from solver import PolicyNet
        device = torch.device(
            "cuda") if torch.cuda.is_available() else torch.device("cpu")
        model = torch.load("model.pt").to(device)
    if Algorithm.Roulette in use_algorithms:
        Weight = [1 for i in range(Action_num)]  # 算子的初始权重，
        UseTimes = [0 for i in range(Action_num)]  # 初始次数，0
        Score = [1 for i in range(Action_num)]  # 算子初始得分，1
        b = 0.5  # 权重变化系数
    if Algorithm.SA in use_algorithms:
        a = 0.95  # a(降温速度)
    state = encode(mos_list, encode_dict)
    reward = get_score(state, pins, ref_width)
    best_state = copy.deepcopy(state)
    best_reward = copy.deepcopy(reward)
    """优化布局"""
    for iter in range(5):
        # for iter in range(1):
        state, reward, best_state, best_reward, T, T_min = init_SA(state, reward, best_state, best_reward)  # 利用爬山法进行参数初始化
        while T > T_min:
            if best_reward > 89.9:
                break
            count = 0
            while count < 20*len(mos_list):
                # 产生新解
                if Algorithm.RL in use_algorithms:
                    state_tensor = torch.tensor(
                        [state], dtype=torch.float).to(device)
                    probs = model(state_tensor)
                    action_dist = torch.distributions.Categorical(probs)
                    action = action_dist.sample().item()
                elif Algorithm.Roulette in use_algorithms:
                    action = selectAndUseOperator(
                        Weight, state, UseTimes)
                else:
                    action = rd.randint(0, Action_num-1)
                new_state = v_compute(state, action)
                # 计算新解的价值
                new_reward = get_score(new_state, pins, ref_width)
                # 更新
                if Algorithm.SA in use_algorithms:
                    if Algorithm.Roulette in use_algorithms:
                        if new_reward >= reward:  # 新解更优
                            state = new_state
                            reward = new_reward
                            if new_reward > best_reward:
                                # with open('best.json', 'w') as f:
                                #     json.dump(decode(new_state, decode_dict),
                                #               f, sort_keys=False, indent=4)
                                best_state = new_state
                                best_reward = new_reward
                                Score[action] += 1.5  # 如果是最优解的话权重增加到1.5
                        else:
                            # if rd.random() < np.exp((new_reward - reward) / T):  # 使用模拟退火算法的接受准则在一定标准下接受劣解
                            if rd.random() < np.exp((new_reward - reward) / T):
                                state = new_state
                                reward = new_reward
                                Score[action] += 0.8  # 满足接受准则的劣解，权重增加0.8
                            else:
                                Score[action] += 0.6  # 不满足接受准则权重仅增加0.6
                        # 更新算子权重，（1-b）应该放前面，这个例子里取b=0.5，无影响
                        Weight[action] = Weight[action] * b + \
                            (1 - b) * (Score[action] / UseTimes[action])
                    else:
                        if new_reward >= reward:  # 新解更优
                            state = new_state
                            reward = new_reward
                            if new_reward > best_reward:
                                # with open('best.json', 'w') as f:
                                #     json.dump(decode(new_state, decode_dict),
                                #               f, sort_keys=False, indent=4)
                                best_state = new_state
                                best_reward = new_reward
                        else:
                            if rd.random() < np.exp((new_reward - reward) / T):  # 使用模拟退火算法的接受准则在一定标准下接受劣解
                                state = new_state
                                reward = new_reward
                else:
                    if Algorithm.Roulette in use_algorithms:
                        if new_reward >= reward:  # 新解更优
                            state = new_state
                            reward = new_reward
                            if new_reward > best_reward:
                                # with open('best.json', 'w') as f:
                                #     json.dump(decode(new_state, decode_dict),
                                #               f, sort_keys=False, indent=4)
                                best_state = new_state
                                best_reward = new_reward
                        # 更新算子权重，（1-b）应该放前面，这个例子里取b=0.5，无影响
                        Weight[action] = Weight[action] * b + \
                            (1 - b) * (Score[action] / UseTimes[action])
                    else:
                        if new_reward >= reward:  # 新解更优
                            state = new_state
                            reward = new_reward
                            if new_reward > best_reward:
                                # with open('best.json', 'w') as f:
                                #     json.dump(decode(new_state, decode_dict),
                                #               f, sort_keys=False, indent=4)
                                best_state = new_state
                                best_reward = new_reward
                        # else:
                        #     if rd.random() < np.exp((new_reward - reward) / T):  # 使用模拟退火算法的接受准则在一定标准下接受劣解
                        #         state = new_state
                        #         reward = new_reward
                count += 1
            T = a*T
    print(best_state, best_reward)
    with open(save_path, 'w') as f:
        json.dump(decode(best_state, decode_dict),
                  f, sort_keys=False, indent=4)
    print(f"cell name:{cell_name}\n晶体管数量:{len(mos_list)}\nbest_score:{best_reward+7.31}\n耗时:{time.time()-start}s\n"+'*'*150)
