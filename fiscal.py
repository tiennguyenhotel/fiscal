#import
import base64

import pandas
import numpy_financial as npf
from IPython.display import HTML
# pandas configuration
pandas.set_option('display.max_rows', None)
pandas.set_option('display.max_columns', None)
pandas.set_option('display.width', 1000)
pandas.set_option('display.colheader_justify', 'center')
pandas.set_option('display.precision', 3)
pandas.options.display.float_format = '{:,.0f}'.format

class Local_Fiscal_Cost_Model:
    def __init__(self,natural_county_name,year,number_of_expected_workers,jobs_multipliers,will_data,HHsize_data,commuting_data,cost_category_data,average_share_of_new_workers_to_the_region=45,discount_rate=1.16,year_discount=10,):
        self.year_discount = year_discount
        self.natural_county_name=natural_county_name.lower().strip().replace(' ','')
        self.year=year
        self.number_of_expected_workers=number_of_expected_workers
        self.jobs_multipliers=jobs_multipliers
        self.average_share_of_new_workers_to_the_region=average_share_of_new_workers_to_the_region/100
        self.discount_rate=discount_rate/100
        self.commuting_residents=self.index_pdframe_config(commuting_data,"work county_state")
        self.resident_share_of_total_workers=self.commuting_residents["resident share of total workers"][self.natural_county_name]
        self.census_hh_size=self.index_pdframe_config(HHsize_data,"county, state")
        self.average_household_size=self.census_hh_size["average hh size"][self.natural_county_name]
        self.expected_direct_indirect_and_induced_workers=self.jobs_multipliers*self.number_of_expected_workers
        self.expected_resident_workers=self.expected_direct_indirect_and_induced_workers*self.resident_share_of_total_workers
        self.B_Expected_resident_workers=round(self.number_of_expected_workers*self.resident_share_of_total_workers,0)
        self.expected_residents=self.expected_resident_workers*self.average_household_size
        self.expected_new_residents=self.average_share_of_new_workers_to_the_region*self.expected_residents
        self.locality_data=self.index_pdframe_config(will_data,"natural county name")
        self.county_id=self.locality_data["govsid"][self.natural_county_name][0]
        self.cost_category=pandas.DataFrame(pandas.read_csv(cost_category_data))
        self.cost_category.columns=self.cost_category.columns.str.lower()
        self.plos_headings=[str(i).lower() for i in self.cost_category["plos headings"]]
        self.expense_data=self.condition_plos_headings()
        self.expense_summary=pandas.DataFrame(data={'Amount':[self.sum(self.expense_data["amount"])],'Per Capita':[self.sum(self.expense_data["per_capita"])]},index=["Total expenditures, ground up"])
        self.output_tableau_data=self.output_tableau(self.expense_data)

    def index_pdframe_config(self, path,index_name):
        return_val = pandas.DataFrame(pandas.read_csv(path))
        return_val.columns = return_val.columns.str.lower()
        return_val.set_index(index_name, inplace=True)
        return_val.index = return_val.index.str.lower()
        return_val.index = return_val.index.str.strip()
        return_val.index = return_val.index.str.replace(' ', '')

        return return_val
    def condition_plos_headings(self):
        data_return=[]
        index=self.check()
        self.population=self.locality_data["population"][index]
        for i in self.plos_headings:
            try:
                if index==False:
                    data_return.append("nan")
                    continue
                else:
                    data_return.append(float(self.locality_data[i][index]))
            except:
                data_return.append("nan")
                continue

        data=self.cost_category.assign(amount=data_return)
        data=data.assign(per_capita=self.get_per_capita(self.population,data_return))
        return data
    def check(self):
        for k in range(len(self.locality_data["govsid"])):
            county_id_check=self.locality_data["govsid"][k]
            year_check=self.locality_data["year4"][k]
            if (county_id_check==self.county_id) and (year_check==self.year):
                return k

        return (False)
    def get_per_capita(self,population,data):
        data_return=[]
        try:
            for i in data:
                value=float(i)
                value=(value*1000)/population
                data_return.append(value)
        except:
            data_return.append("nan")
        return data_return
    def sum(self,data):
        data_return=[i for i in data if str(i)!="nan"]
        sum_data=round(sum(data_return),0)
        return sum_data
    def output_tableau(self,data):
        newoutput= data.dropna()
        newoutput=newoutput.groupby(["major category"]).agg({'per_capita':'sum'})
        spending=[npf.pv(self.discount_rate,self.year_discount,i) for i in newoutput["per_capita"]]
        newoutput=newoutput.assign(ten_year_per_capita=spending)
        A_impact_per_project=[self.expected_new_residents*i for i in newoutput["per_capita"]]
        newoutput=newoutput.assign(A_total_impact_per_project=A_impact_per_project)
        A_ten_year_npv_impact=[npf.pv(self.discount_rate,self.year_discount,k) for k in A_impact_per_project]
        newoutput=newoutput.assign(A_ten_year_npv_impact=A_ten_year_npv_impact)
        B_total_impact_per_project=[n*self.B_Expected_resident_workers for n in newoutput["per_capita"]]
        newoutput=newoutput.assign(B_total_impact_per_project=B_total_impact_per_project)
        B_ten_year_npv_impact=[npf.pv(self.discount_rate,self.year_discount,k) for k in B_total_impact_per_project]
        data_return=newoutput.assign(B_ten_year_npv_impact=B_ten_year_npv_impact)

        return data_return.round(0)

    def csv(self,df, title="Download CSV file", filename="data.csv"):
        csv = df.to_csv()
        b64 = base64.b64encode(csv.encode())
        payload = b64.decode()
        html = '<a download="{filename}" href="data:text/csv;base64,{payload}" target="_blank">{title}</a>'
        html = html.format(payload=payload, title=title, filename=filename)
        return HTML(html)

