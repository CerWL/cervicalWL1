package function

import (
	"encoding/json"
	"log"

	logger "github.com/paulxiong/cervical/webpage/2_api_server/log"
	m "github.com/paulxiong/cervical/webpage/2_api_server/models"
)

// ProjectInfo 项目的描述信息, 存到工作目录的info.json
type ProjectInfo struct {
	ID      int64  `json:"id"      example:"1"`             //任务ID
	DID     int64  `json:"did"     example:"1"`             //数据集的id
	DDir    string `json:"ddir"    example:"dataset dir"`   //数据集的目录
	Dir     string `json:"dir"     example:"project dir"`   //项目任务执行的目录名，调试时候很有用
	Status  int    `json:"status"  example:"4"`             //任务的状态码
	Type    int    `json:"type"    example:"1"`             //项目类型 0 未知 1 训练 2 预测
	Types   []int  `json:"types"   example:"7"`             //训练哪几个类型的细胞
	ModPath string `json:"modpath" example:"path of model"` //模型文件的路径
}

// NewProjectJSONFile 创建项目
func NewProjectJSONFile(id int64, types []int, dirname string, status int, _type int, did int64) {
	dt, _ := m.GetOneDatasetByID(int(did))

	p := ProjectInfo{
		ID:      id,
		DID:     did,
		DDir:    dt.Dir,
		Dir:     dirname,
		Status:  status,
		Type:    _type,
		Types:   types,
		ModPath: "",
	}
	data, err := json.MarshalIndent(p, "", " ") //这里返回的data值，类型是[]byte
	if err != nil {
		log.Println("ERROR:", err)
	}
	info := projectsDir + "/" + dirname + "/info.json"
	logger.Info.Println(info)
	writeJSON(info, data)
}
