import itertools
from typing import List

from car import Car
from node import Node
from scrdr_tree import SCRDRTree


def get_objects_dict(filepath):
    lines = open(filepath, 'r').readlines()

    objects = {}

    for line in lines:
        line = line.strip()
        if line == '':
            continue

        line = line.split(',')

        gold = line[6]
        label = 'unacc'

        obj = Car(line[0], line[1], line[2], line[3], line[4], line[5], label)

        if label not in objects:
            objects[label] = {}
            objects[label][label] = []

        if gold not in objects[label]:
            objects[label][gold] = []

        objects[label][gold].append(obj)

    return objects


def generate_rules(obj: Car):
    rule1 = 'obj.buying == "{}"'.format(obj.buying)
    rule2 = 'obj.maint == "{}"'.format(obj.maint)
    rule3 = 'obj.doors == "{}"'.format(obj.doors)
    rule4 = 'obj.persons == "{}"'.format(obj.persons)
    rule5 = 'obj.lug_boot == "{}"'.format(obj.lug_boot)
    rule6 = 'obj.safety == "{}"'.format(obj.safety)

    uni_rules = [rule1, rule2, rule3, rule4, rule5, rule6]
    rules = [rule1, rule2, rule3, rule4, rule5, rule6]

    for rule in itertools.combinations(uni_rules, 2):
        rules.append(' and '.join(list(rule)))

    # for rule in itertools.combinations(uni_rules, 3):
    #     rules.append(' and '.join(list(rule)))

    # for rule in itertools.combinations(uni_rules, 4):
    #     rules.append(' and '.join(list(rule)))

    # for rule in itertools.combinations(uni_rules, 5):
    #     rules.append(' and '.join(list(rule)))

    # for rule in itertools.combinations(uni_rules, 6):
    #     rules.append(' and '.join(list(rule)))

    return rules

def count_matching(objects: List[Car], rule_not_in: List[str]):
    count = {}
    matching = {}
    for obj in objects:
        rules = generate_rules(obj)
        for rule in rules:
            if rule in rule_not_in:
                continue
            count[rule] = count.setdefault(rule, 0) + 1
            matching.setdefault(rule, []).append(obj)

    return count, matching

def sastify(obj, rule):
    return eval(rule)

def fire(rule, corner_stone_cases):
    for obj in corner_stone_cases:
        if sastify(obj, rule):
            return True
    return False

def generate_rules_from_objectset(objects: List[Car]):
    rules = []
    for obj in objects:
        rules += generate_rules(obj)
    return rules

class SCRDRLearner(SCRDRTree):
    def __init__(self, improved_threshold=2, matched_threshold=2):
        self.improved_threshold = improved_threshold
        self.matched_threshold = matched_threshold

    def find_most_improving_rule_for_label(self, start_label, correct_label, correct_counts, wrong_objects):
        impove_counts, affected_objects = count_matching(wrong_objects, [])

        max_improve = -1000000
        best_rule = ''
        for rule in impove_counts:
            count = impove_counts[rule]
            if rule in correct_counts:
                count -= correct_counts[rule]

            if count > max_improve:
                max_improve = count
                best_rule = rule

        if max_improve == -1000000:
            affected_objects[best_rule] = []

        return best_rule, max_improve, affected_objects[best_rule]

    def find_most_efficient_rule(self, start_label, objects, correct_counts):
        max_improve = -1000000
        best_rule = ''
        correct_label = ''
        corner_stone_cases = []

        for label in objects:
            if label == start_label:
                continue
            if len(objects[label]) <= max_improve or len(objects[label]) < self.improved_threshold:
                continue

            temp_rule, imp, affected_objects = self.find_most_improving_rule_for_label(start_label, correct_label, correct_counts, objects[label])

            if imp >= self.improved_threshold and imp > max_improve:
                max_improve = imp
                best_rule = temp_rule
                correct_label = label
                corner_stone_cases = affected_objects

        need_to_correct_objects = {}
        error_raising_objects = []
        if max_improve > -1000000:
            for label in objects:
                if label != correct_label:
                    for obj in objects[label]:
                        if sastify(obj, best_rule):
                            need_to_correct_objects.setdefault(label, []).append(obj)
                            if label == start_label:
                                error_raising_objects.append(obj)

        return best_rule, correct_label, max_improve, corner_stone_cases, need_to_correct_objects, error_raising_objects

    def find_most_matching_rule(self, matching_counts):
        correct_label = ''
        best_rule = ''
        max_count = -1000000

        for label in matching_counts:
            for rule in matching_counts[label]:
                if matching_counts[label][rule] >= self.matched_threshold and matching_counts[label][rule] > max_count:
                    max_count = matching_counts[label][rule]
                    best_rule = rule
                    correct_label = label

        return best_rule, correct_label

    def build_node_for_objectset(self, objects, root):
        corner_stone_case_rules = generate_rules_from_objectset(root.corner_stone_cases)

        matching_counts = {}
        matching_objects = {}
        for label in objects:
            matching_counts[label], matching_objects[label] = count_matching(objects[label], corner_stone_case_rules)

        total = 0
        for label in objects:
            total += len(objects[label])

        curr_node = root
        else_child = False

        while True:
            rule, correct_label = self.find_most_matching_rule(matching_counts)

            if rule == '':
                break

            corner_stone_cases = matching_objects[correct_label][rule]

            need_to_correct_objects = {}
            for label in objects:
                if rule in matching_objects[label]:
                    if label != correct_label:
                        need_to_correct_objects[label] = matching_objects[label][rule]
                    for obj in matching_objects[label][rule]:
                        rules  = generate_rules(obj)
                        for rule1 in rules:
                            if rule1 not in matching_counts[label]:
                                continue
                            matching_counts[label][rule1] -= 1

            node = Node(rule, 'obj.conclusion = "{}"'.format(correct_label), curr_node, None, None, corner_stone_cases)

            if not else_child:
                curr_node.except_child = node
                else_child = True
            else:
                curr_node.else_child = node

            curr_node = node
            self.build_node_for_objectset(need_to_correct_objects, curr_node)

    def learn(self, filepath):
        self.root = Node('True', 'obj.conclusion == "unacc"', None, None, None, [], 0)

        objects = get_objects_dict(filepath)

        curr_node = self.root
        label = 'unacc'
        correct_counts = {}

        for obj in objects[label][label]:
            rules = generate_rules(obj)
            for rule in rules:
                correct_counts[rule] = correct_counts.setdefault(rule, 0) + 1

        object_set = objects[label]

        else_child = False
        curr_node1 = curr_node
        while True:
            rule, correct_label, improve, corner_stone_cases, need_to_correct_objects, error_raising_objects = self.find_most_efficient_rule(label, object_set, correct_counts)
            if improve < self.improved_threshold:
                break

            node = Node(rule, 'obj.conclusion == "{}"'.format(correct_label), curr_node, None, None, corner_stone_cases, 1)

            if not else_child:
                curr_node1.except_child = node
                else_child = True
            else:
                curr_node1.else_child = node

            curr_node1 = node

            for obj in corner_stone_cases:
                object_set[correct_label].remove(obj)

            for label in need_to_correct_objects:
                for obj in need_to_correct_objects[label]:
                    object_set[label].remove(obj)

            for obj in error_raising_objects:
                rules = generate_rules(obj)
                for rule in rules:
                    if rule in correct_counts:
                        correct_counts[rule] -= 1

            self.build_node_for_objectset(need_to_correct_objects, curr_node1)
