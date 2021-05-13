import swagger_server.response_code.utils as ut
from swagger_server.database.models import FabricPerson

if __name__ == "__main__":

    person1 = FabricPerson()
    person1.name = 'Fname Lname'
    person1.co_person_id = '1234'
    person1.oidc_claim_sub = 'http://cilogon.org/serverT/users/12345'

    #print(ut.comanage_check_active_person(person1))
    print(ut.comanage_list_people_matches(given='Fname', family='Lname'))
    print(ut.comanage_get_person_identifier('1234', 'oidcsub'))