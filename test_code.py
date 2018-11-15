import Fact
import Action_Rule

global ar, effect_set, constraint_set

i1 = Fact.Fact.make_fact_from_string("Move_To(Init, Intent)")

c1 =  Fact.Fact.make_fact_from_string("+Hand_At(Intent)")
c2 =  Fact.Fact.make_fact_from_string("+Place_Touching(Red, Intent)")

e1 = Fact.Fact.make_fact_from_string("+Hand_Touching(Red)")
e2 = Fact.Fact.make_fact_from_string("-Hand_At(Init)")
e3 = Fact.Fact.make_fact_from_string("+Hand_At(Intent)")

effect_set = Action_Rule.Effect_Set([e1, e2, e3])
constraint_set = Action_Rule.Constraint_Set([c1, c2])

ar = Action_Rule.Action_Rule(i1, constraint_set, effect_set)
print(ar)