tag="develop"
user="fiware"

repo_spassword="keystone-spassword"
pack_spassword="package-keystone-spassword.sh"
url_spassword="https://pdihub.hi.inet/${user}/${repo_spassword}/archive/${tag}.tar.gz"

dir=~/fiware-keystone
rm -fR $dir && mkdir -p $dir

curl -s --insecure -L "${url_spassword}" | tar zxvf - -C ${dir}

cd ${dir}/${repo_spassword}-${tag}
source ./${pack_spassword}

find . -name "*.rpm" -exec sudo rpm -Uvh {} \;
