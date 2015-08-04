tag="develop"
user="telefonicaid"

repo_scim="fiware-keystone-scim"
pack_scim="package-keystone-scim.sh"
url_scim="https://github.com/${user}/${repo_scim}/archive/${tag}.tar.gz"

dir=~/fiware-keystone
rm -fR $dir && mkdir -p $dir

curl -s --insecure -L "${url_scim}" | tar zxvf - -C ${dir}

cd ${dir}/${repo_scim}-${tag}
source ./${pack_scim}

find . -name "*.rpm" -exec sudo rpm -Uvh {} \;
