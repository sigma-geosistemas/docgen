## Schema {{ schema.name }}

* Descrição: {{ schema.description }}

{% if schema.tables() %}
### Tabelas

{% for table in schema.tables() %}

#### {{ table.name }}

* Descrição: {{ table.description }}

##### Colunas

{% for column in table.columns() %}
* *{{ column.name }}*

	* Descrição: {{ column.description }}
	* Tipo: {{ column.formatted_type() }}
	* Null? {{ column.formatted_is_nullable() }}
	* Padrão: {{ column.formatted_default() }}

{% endfor %}


{% if table.indexes() %}

##### Índices

{% for idx in table.indexes() %}

* *{{ idx.name }}*

	* Tipo: {{ idx.itype }}
	* Campos: {% for field in idx.fields %}{% if loop.index0 != 0 %}, {% endif %}{{ field }}{% endfor %}

{% endfor %}

{% endif %}



{% if table.constraints() %}

##### Constraints

{% for con in table.constraints() %}

* *{{ con.name }}*

	* Definição: {{ con.definition }}

{% endfor %}

{% endif %}


{% endfor %}

{% endif %}

{% if schema.views() %}
#### Views

{% for view in schema.views() %}

##### {{ view.name }}

* Descrição: {{ view.description }}

##### Colunas

{% for column in view.columns() %}
* *{{ column.name }}*

	* Descrição: {{ column.description }}
	* Tipo: {{ column.formatted_type() }}

{% endfor %}

{% endfor %}

{% endif %}