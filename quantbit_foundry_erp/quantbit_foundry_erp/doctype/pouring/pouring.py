# Copyright (c) 2023, Quantbit Technologies Pvt ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Pouring(Document):
	def before_save(self):
		self.validate_poring_weight()
		self.calculating_power_consumption()
		self.validate_stock()
		self.validate_retained_items()
		self.calculating_power_consumption_amount()
		self.set_datd_in_naming_fields()

	def before_submit(self):
		self.manifacturing_stock_entry()
		self.manifacturing_retained_items()
		self.calculating_power_consumption_amount()
		

	@frappe.whitelist()
	def get_details_pattern_master(self):
		pattern_details = self.get("pattern_details")

		for i in pattern_details:
			if i.pattern_code and i.poured_boxes:
				swcore = frappe.get_value("Foundry Setting",self.company,"sw_core")
				twcasting = frappe.get_value("Foundry Setting",self.company,"tw_casting")
				pm_doc = frappe.get_all("Casting Material Details", 
												filters = {"parent": i.pattern_code},
												fields = ["item_code","item_name","weight","qty","uom"])
				pm_rr_weight =frappe.get_value('Pattern Master',i.pattern_code ,'rr_weight')
				casting_weight =frappe.get_value('Pattern Master',i.pattern_code ,'casting_weight')
				
				for d in pm_doc:

					rr_weight=(pm_rr_weight/casting_weight)*(d.weight)
					total_weight = ((d.weight)+ rr_weight ) * (i.poured_boxes * d.qty)


					self.append("casting_details",{
						'item_code': d.item_code ,
						'item_name': d.item_name,
						'pattern': i.pattern_code,
						'quantitybox': d.qty ,
						'total_quantity':i.poured_boxes * d.qty,
						'casting_weight' : d.weight,
						'rr_weight' : rr_weight,
						'total_weight' : total_weight ,
						'target_warehouse' : twcasting ,
						'sales_order' : i.sales_order,
					},),


					cmd_doc = frappe.get_all("Core Material Details", 
													filters = {"parent": i.pattern_code, "casting_item_code" : d.item_code},
													fields = ["casting_item_code","item_code","item_name","qty","uom"])
					# rr_weight =frappe.get_value('Pattern Master',i.pattern_code ,'rr_weight')
					for cmd in cmd_doc:
						


						self.append("core_details",{
							"casting_item_code" : cmd.casting_item_code,
							'item_code': cmd.item_code ,
							'item_name': cmd.item_name,
							'pattern': i.pattern_code ,
							'qty': cmd.qty * (i.poured_boxes * d.qty) ,
							'uom':cmd.uom,
							"warehouse" : swcore ,
							'stock' : self.get_available_quantity(cmd.item_code , swcore),

						},),	
		self.total_pouring_weight = self.calculating_total_weight("casting_details","total_weight")
		if self.total_consumed_weight and self.total_pouring_weight:
				self.total_weight_difference =  self.total_consumed_weight - self.total_pouring_weight
		self.validate_poring_weight_without_interupt()

	@frappe.whitelist()
	def calculating_total_weight(self,child_table ,total_field):
		casting_details = self.get(child_table)
		total_pouring_weight = 0
		for i in casting_details:
			field_data = i.get(total_field)
			if field_data:
				total_pouring_weight = total_pouring_weight + field_data
		return total_pouring_weight
	
		# self.total_pouring_weight= total_pouring_weight


	@frappe.whitelist()
	def get_details_grade_master(self):
		if self.grade:
			if self.furnece:
				swcharge = frappe.get_value("Foundry Setting",self.company,"sw_charge")
				total_furnece_kg = frappe.get_value("Furnece Master",self.furnece,"furnece_capcity")
				gid_doc = frappe.get_all("Grade Items Details", 
													filters = {"parent": self.grade},
													fields = ["item_code","item_name","item_group","percentage"])

				for gid in gid_doc:
						

						self.append("change_mix_details",{
							'item_code': gid.item_code ,
							'item_name': gid.item_name,
							'item_group': gid.item_group,
							'quantity': (gid.percentage * total_furnece_kg)/100,
							'warehouse': swcharge,
							'stock' : self.get_available_quantity(gid.item_code , swcharge) ,
						
						},),
			else:
				frappe.throw("Please select Furnece")

			self.total_consumed_weight = self.calculating_total_weight("change_mix_details","quantity")

			if self.total_consumed_weight and self.total_pouring_weight:
				self.total_weight_difference =  self.total_consumed_weight - self.total_pouring_weight


	@frappe.whitelist()
	def validate_poring_weight(self):
		if self.total_consumed_weight < self.total_pouring_weight:
			frappe.throw(f'"Total Pouring Weight" must be less than "Total Consumed Weight"')

	@frappe.whitelist()
	def validate_poring_weight_without_interupt(self):
		if self.total_consumed_weight:
				if self.total_consumed_weight < self.total_pouring_weight:
					frappe.msgprint(f'"Total Pouring Weight" must be less than "Total Consumed Weight"')
		else:
			frappe.msgprint("Please select Grade")


	@frappe.whitelist()
	def calculating_power_consumption(self):
		if self.power_reading_initial and  self.power_reading_final:
			self.power_consumed = self.power_reading_final - self.power_reading_initial
			if self.power_consumed < 0 :
				frappe.throw("The 'Power Consumed' should not be negatine")

			self.calculating_power_consumption_amount()
		
	# @frappe.whitelist()
	# def calculating_power_consumption_amount(self):
	# 	power_consumption = frappe.get_all("Power Consumption Details",
	# 								 				filters = {"parent": self.company , "from_date" : ['<=',self.heat_date]},
	# 												fields = ["from_date","amount_per_unit",] , order_by = "from_date DESC",limit =1)
		
	# 	if power_consumption:
	# 		self.power_consumption_charges = self.power_consumed * power_consumption[0].amount_per_unit
	# 	else:
	# 		frappe.msgprint("Please set 'Power Consumption'")
		# if power_consumption:

			#frappe.get_all("Child Wages Master",filters = {"parent": cor[0].name ,"from_date": ['<=',self.date]},fields = ["wages_per_hour"], order_by = 'from_date DESC')

	@frappe.whitelist()
	def get_stock_change_mix_details(self):
		for cmd in self.get("change_mix_details"):
			if cmd.item_code and cmd.warehouse:
				cmd.stock = self.get_available_quantity(cmd.item_code , cmd.warehouse)
	
	@frappe.whitelist()
	def get_stock_core_details(self):
		for cd in self.get("core_details"):
			if cd.item_code and cd.warehouse:
				cd.stock = self.get_available_quantity(cd.item_code , cd.warehouse)


	def get_available_quantity(self,item_code, warehouse):
		filters = 	{"item_code": item_code,"warehouse": warehouse}
		fields = ["actual_qty"]
		result = frappe.get_all("Bin", filters=filters, fields=fields)
		if result and result[0].get("actual_qty"):
			return result[0].get("actual_qty")
		else:
			return 0
		

	@frappe.whitelist()
	def validate_stock(self):
		for vsk in self.get("change_mix_details"):
			if vsk.quantity > vsk.stock :
				frappe.throw(f'There is not enough stock present in warehouse "{vsk.warehouse}" of item "{vsk.item_name}" to proceed with pouring entry')

		for stk in self.get("core_details"):
			if stk.qty > stk.stock :
				frappe.throw(f'There is not enough stock present in warehouse "{stk.warehouse}" of item "{stk.item_name}" to proceed with pouring entry')

	@frappe.whitelist()
	def validate_retained_items(self):
		total_sum =0
		for ri in self.get("retained_items"):
			if ri.total_quantity:
				total_sum = total_sum + ri.total_quantity

		if self.total_weight_difference:
			if self.total_weight_difference != total_sum:
				frappe.throw(f"The total sum of 'Total Quantity' should be equal to { self.total_weight_difference} ")
		
	@frappe.whitelist()
	def calculating_power_consumption_amount(self):
		power_consumption = frappe.get_all("Power Consumption Details",
									 				filters = {"parent": self.company , "from_date" : ['<=',self.heat_date]},
													fields = ["from_date","amount_per_unit",] , order_by = "from_date DESC",limit =1)
		expense_head_account = frappe.get_value("Power Consumption",self.company,"expense_head_account")

		if power_consumption:
			additional_cost_details = self.get("additional_cost_details")
			rows_to_remove = [d for d in self.get("additional_cost_details") if d.is_electricity_expense]
			for d in rows_to_remove:
				additional_cost_details.remove(d)




			if power_consumption:
				self.append("additional_cost_details",{
								'discription': "Electricity Expense" ,
								'expense_head_account': expense_head_account,
								'amount': self.power_consumed * power_consumption[0].amount_per_unit,
								'is_electricity_expense': True,
							},),
		else:
			frappe.msgprint("Please set 'Power Consumption'")


	def set_datd_in_naming_fields(self):
		list_data =[]
		for d in self.get('casting_details'):
			list_data.append(d.item_name)
		self.naming_fields = str(list_data)

		
	@frappe.whitelist()
	def manifacturing_stock_entry(self):
		for cd in self.get("casting_details"):      
			se = frappe.new_doc("Stock Entry")
			se.stock_entry_type = "Manufacture"
			se.company = self.company
			se.posting_date = self.heat_date
			for g in self.get("change_mix_details"):
				se.append(
						"items",
						{
							"item_code": g.item_code,
							"qty":  (cd.total_weight * g.quantity) / self.total_consumed_weight,
							"s_warehouse": g.warehouse,
						},)

			for core in self.get("core_details"):
				if core.casting_item_code == cd .item_code:
					se.append(
							"items",
							{
								"item_code": core.item_code,
								"qty": core.qty,
								"s_warehouse": core.warehouse,
							},)

			se.append(
						"items",
						{
							"item_code": cd.item_code,
							"qty": cd.total_quantity ,
							"t_warehouse": cd.target_warehouse,
							'is_finished_item':True
						},) 
			for acd in self.get("additional_cost_details"):
				se.append(
						"additional_costs",
						{
							"expense_account":acd.expense_head_account,
							"description": acd.discription,
							"amount": (acd.amount* cd.total_weight) / self.total_pouring_weight,

						},)
			

			se.custom_pouring = self.name	
			se.insert()
			se.save()
			se.submit()

	@frappe.whitelist()
	def manifacturing_retained_items(self):
		for ri in self.get("retained_items"):      
			se = frappe.new_doc("Stock Entry")
			se.stock_entry_type = "Manufacture"
			se.company = self.company
			se.posting_date = self.heat_date
			for p in self.get("change_mix_details"):
				se.append(
						"items",
						{
							"item_code": p.item_code,
							"qty":  (ri.total_quantity * p.quantity) / self.total_consumed_weight,
							"s_warehouse": p.warehouse,
						},)


			se.append(
						"items",
						{
							"item_code": ri.item_code,
							"qty": ri.total_quantity ,
							"t_warehouse": ri.target_warehouse,
							'is_finished_item':True
						},)

			se.custom_pouring = self.name	
			se.insert()
			se.save()
			se.submit()


	@frappe.whitelist()
	def calculation_after_short_quentity(self):
		for pd in self.get('pattern_details'):
			pm_rr_weight =frappe.get_value('Pattern Master',pd.pattern_code ,'rr_weight')
			casting_weight =frappe.get_value('Pattern Master',pd.pattern_code ,'casting_weight')

			for cd in self.get('casting_details'):
				# if cd.short_quantity:
					if pd.pattern_code ==  cd.pattern:
						cd.total_quantity = (cd.quantitybox - cd.short_quantity)* pd.poured_boxes
						rr_weight = (pm_rr_weight/casting_weight)*(cd.casting_weight)
						total_weight = ((cd.casting_weight)+ rr_weight ) * (cd.total_quantity)
						# frappe.msgprint(str(rr_weight)+"====="+str(total_weight))
						cd.rr_weight = rr_weight
						cd.total_weight = total_weight

		self.total_pouring_weight = self.calculating_total_weight("casting_details","total_weight")
		if self.total_consumed_weight and self.total_pouring_weight:
				self.total_weight_difference =  self.total_consumed_weight - self.total_pouring_weight
		self.validate_poring_weight_without_interupt()